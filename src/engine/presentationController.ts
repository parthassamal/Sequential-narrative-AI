/**
 * Sequential Presentation Controller State Machine
 * 
 * Implements adaptive presentation with six states:
 * - PRESENT, MONITOR, ADJUST, NEXT, COMMIT, UNDO
 * - Adaptive pacing: T_expose = T_base - α·h(t|x) - β·(dC/dt)
 * - Confidence-triggered commitment
 */

import { EnhancedDecisionState } from '../types';

// State Machine States
export type PresentationState = 
  | 'PRESENT'   // Display NRU in full focus
  | 'MONITOR'   // Observe real-time signals
  | 'ADJUST'    // Slow pacing when hesitation high
  | 'NEXT'      // Advance to next NRU
  | 'COMMIT'    // Trigger playback/selection
  | 'UNDO';     // Handle quick cancel

// Events that trigger state transitions
export type PresentationEvent =
  | { type: 'START_PRESENT'; nruIndex: number }
  | { type: 'MONITOR_TICK' }
  | { type: 'HIGH_HESITATION' }
  | { type: 'CONFIDENCE_THRESHOLD_MET' }
  | { type: 'EXPOSURE_COMPLETE' }
  | { type: 'USER_NEXT' }
  | { type: 'USER_PREVIOUS' }
  | { type: 'USER_SELECT' }
  | { type: 'QUICK_CANCEL' }
  | { type: 'UNDO_COMPLETE' };

// Controller configuration
export interface PresentationConfig {
  baseExposureTime: number;      // T_base in seconds (default: 10)
  minExposureTime: number;       // Minimum time before commit (default: 3)
  hesitationAlpha: number;       // α coefficient for hesitation
  confidenceBeta: number;        // β coefficient for confidence change
  confidenceThreshold: number;   // τ_base for commitment
  quickCancelWindow: number;     // Seconds to detect quick cancel (default: 30)
  maxUncertainty: number;        // σ_max for uncertainty guardrail
}

// State context
export interface PresentationContext {
  currentState: PresentationState;
  currentNruIndex: number;
  totalNrus: number;
  exposureStartTime: number | null;
  currentExposureTime: number;
  adaptedExposureTarget: number;
  
  // Decision state
  decisionState: EnhancedDecisionState | null;
  previousConfidence: number;
  confidenceChangeRate: number;  // dC/dt
  
  // Commit tracking
  pendingCommitId: string | null;
  commitTimestamp: number | null;
  
  // History
  viewedNrus: number[];
  stateHistory: Array<{ state: PresentationState; timestamp: number }>;
}

// Default configuration
const DEFAULT_CONFIG: PresentationConfig = {
  baseExposureTime: 10,
  minExposureTime: 3,
  hesitationAlpha: 2,      // High hesitation adds up to 2 seconds
  confidenceBeta: 3,       // Fast confidence rise subtracts up to 3 seconds
  confidenceThreshold: 0.7,
  quickCancelWindow: 30,
  maxUncertainty: 0.7,
};

/**
 * Sequential Presentation Controller
 * 
 * Manages the state machine for displaying NRUs one at a time
 * with adaptive pacing based on user decision state.
 */
export class PresentationController {
  private config: PresentationConfig;
  private context: PresentationContext;
  private onStateChange?: (context: PresentationContext) => void;
  private onCommitTriggered?: (nruIndex: number, triggerId: string) => void;
  private onUndoTriggered?: (triggerId: string) => void;

  constructor(
    config: Partial<PresentationConfig> = {},
    callbacks?: {
      onStateChange?: (context: PresentationContext) => void;
      onCommitTriggered?: (nruIndex: number, triggerId: string) => void;
      onUndoTriggered?: (triggerId: string) => void;
    }
  ) {
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.context = this.createInitialContext();
    
    if (callbacks) {
      this.onStateChange = callbacks.onStateChange;
      this.onCommitTriggered = callbacks.onCommitTriggered;
      this.onUndoTriggered = callbacks.onUndoTriggered;
    }
  }

  private createInitialContext(): PresentationContext {
    return {
      currentState: 'PRESENT',
      currentNruIndex: 0,
      totalNrus: 0,
      exposureStartTime: null,
      currentExposureTime: 0,
      adaptedExposureTarget: this.config.baseExposureTime,
      decisionState: null,
      previousConfidence: 0.5,
      confidenceChangeRate: 0,
      pendingCommitId: null,
      commitTimestamp: null,
      viewedNrus: [],
      stateHistory: [],
    };
  }

  /**
   * Initialize controller with NRU count
   */
  initialize(totalNrus: number): void {
    this.context = this.createInitialContext();
    this.context.totalNrus = totalNrus;
    this.transitionTo('PRESENT');
  }

  /**
   * Send event to state machine
   */
  send(event: PresentationEvent): void {
    const previousState = this.context.currentState;
    
    switch (this.context.currentState) {
      case 'PRESENT':
        this.handlePresentState(event);
        break;
      case 'MONITOR':
        this.handleMonitorState(event);
        break;
      case 'ADJUST':
        this.handleAdjustState(event);
        break;
      case 'NEXT':
        this.handleNextState(event);
        break;
      case 'COMMIT':
        this.handleCommitState(event);
        break;
      case 'UNDO':
        this.handleUndoState(event);
        break;
    }

    // Notify if state changed
    if (this.context.currentState !== previousState && this.onStateChange) {
      this.onStateChange(this.context);
    }
  }

  /**
   * Update decision state (called from telemetry)
   */
  updateDecisionState(state: EnhancedDecisionState): void {
    const previousConfidence = this.context.decisionState?.commitProbability ?? 0.5;
    const timeDelta = 1; // Assume 1 second updates
    
    this.context.decisionState = state;
    this.context.confidenceChangeRate = 
      (state.commitProbability - previousConfidence) / timeDelta;
    this.context.previousConfidence = previousConfidence;
    
    // Recalculate adaptive exposure time
    this.updateAdaptedExposureTime();
    
    // Check for state transitions based on new state
    if (this.context.currentState === 'MONITOR') {
      this.checkMonitorTransitions();
    }
  }

  /**
   * Compute adaptive exposure time
   * T_expose = T_base - α·h(t|x) - β·(dC/dt)
   */
  private updateAdaptedExposureTime(): void {
    const { baseExposureTime, hesitationAlpha, confidenceBeta } = this.config;
    const state = this.context.decisionState;
    
    if (!state) {
      this.context.adaptedExposureTarget = baseExposureTime;
      return;
    }
    
    // α term: High hesitation ADDS time (negative of negative)
    // When hesitation is high, we want MORE time, so we ADD
    const hesitationAdjustment = -hesitationAlpha * (state.hesitationScore - 0.5);
    
    // β term: Rising confidence SUBTRACTS time (faster advance)
    const confidenceAdjustment = -confidenceBeta * Math.max(0, this.context.confidenceChangeRate);
    
    // Final exposure time
    let adapted = baseExposureTime + hesitationAdjustment + confidenceAdjustment;
    
    // Clamp to reasonable range
    adapted = Math.max(this.config.minExposureTime, Math.min(20, adapted));
    
    this.context.adaptedExposureTarget = adapted;
  }

  /**
   * Check if commit should be triggered
   * Three-way gate: C_cal > τ AND t > t_min AND σ < σ_max
   */
  private shouldTriggerCommit(): boolean {
    const state = this.context.decisionState;
    if (!state) return false;
    
    const { minExposureTime, confidenceThreshold, maxUncertainty } = this.config;
    
    // Gate 1: Confidence threshold
    const confidenceGate = state.commitProbability > confidenceThreshold;
    
    // Gate 2: Minimum exposure time
    const exposureGate = this.context.currentExposureTime >= minExposureTime;
    
    // Gate 3: Uncertainty guardrail
    const uncertaintyGate = state.epistemicUncertainty < maxUncertainty;
    
    return confidenceGate && exposureGate && uncertaintyGate;
  }

  // State handlers

  private handlePresentState(event: PresentationEvent): void {
    switch (event.type) {
      case 'START_PRESENT':
        this.context.currentNruIndex = event.nruIndex;
        this.context.exposureStartTime = Date.now();
        this.context.currentExposureTime = 0;
        if (!this.context.viewedNrus.includes(event.nruIndex)) {
          this.context.viewedNrus.push(event.nruIndex);
        }
        // Immediately transition to MONITOR
        this.transitionTo('MONITOR');
        break;
      
      case 'USER_NEXT':
      case 'USER_PREVIOUS':
        this.transitionTo('NEXT');
        break;
      
      case 'USER_SELECT':
        this.transitionTo('COMMIT');
        break;
    }
  }

  private handleMonitorState(event: PresentationEvent): void {
    switch (event.type) {
      case 'MONITOR_TICK':
        // Update exposure time
        if (this.context.exposureStartTime) {
          this.context.currentExposureTime = 
            (Date.now() - this.context.exposureStartTime) / 1000;
        }
        this.checkMonitorTransitions();
        break;
      
      case 'HIGH_HESITATION':
        this.transitionTo('ADJUST');
        break;
      
      case 'CONFIDENCE_THRESHOLD_MET':
        if (this.shouldTriggerCommit()) {
          this.transitionTo('COMMIT');
        }
        break;
      
      case 'EXPOSURE_COMPLETE':
        this.transitionTo('NEXT');
        break;
      
      case 'USER_NEXT':
      case 'USER_PREVIOUS':
        this.transitionTo('NEXT');
        break;
      
      case 'USER_SELECT':
        this.transitionTo('COMMIT');
        break;
    }
  }

  private checkMonitorTransitions(): void {
    const state = this.context.decisionState;
    if (!state) return;
    
    // Check for high hesitation -> ADJUST
    if (state.hesitationScore > 0.7 && state.epistemicUncertainty > 0.5) {
      this.send({ type: 'HIGH_HESITATION' });
      return;
    }
    
    // Check for commit trigger
    if (this.shouldTriggerCommit()) {
      this.send({ type: 'CONFIDENCE_THRESHOLD_MET' });
      return;
    }
    
    // Check for exposure complete (auto-advance)
    if (this.context.currentExposureTime >= this.context.adaptedExposureTarget) {
      this.send({ type: 'EXPOSURE_COMPLETE' });
    }
  }

  private handleAdjustState(event: PresentationEvent): void {
    switch (event.type) {
      case 'MONITOR_TICK':
        // In ADJUST, we extend the exposure time
        // Check if hesitation has decreased
        const state = this.context.decisionState;
        if (state && state.hesitationScore < 0.5) {
          // Return to normal monitoring
          this.transitionTo('MONITOR');
        }
        break;
      
      case 'USER_NEXT':
      case 'USER_PREVIOUS':
        this.transitionTo('NEXT');
        break;
      
      case 'USER_SELECT':
        this.transitionTo('COMMIT');
        break;
    }
  }

  private handleNextState(_: PresentationEvent): void {
    // NEXT is a transient state that immediately transitions
    if (this.context.currentNruIndex < this.context.totalNrus - 1) {
      this.context.currentNruIndex++;
    }
    this.transitionTo('PRESENT');
    this.send({ type: 'START_PRESENT', nruIndex: this.context.currentNruIndex });
  }

  private handleCommitState(event: PresentationEvent): void {
    switch (event.type) {
      case 'QUICK_CANCEL':
        // User cancelled within window
        this.transitionTo('UNDO');
        break;
      
      default:
        // Generate commit ID and notify
        this.context.pendingCommitId = `commit_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        this.context.commitTimestamp = Date.now();
        
        if (this.onCommitTriggered) {
          this.onCommitTriggered(
            this.context.currentNruIndex,
            this.context.pendingCommitId
          );
        }
        break;
    }
  }

  private handleUndoState(_: PresentationEvent): void {
    // Reset and return to monitoring
    if (this.context.pendingCommitId && this.onUndoTriggered) {
      this.onUndoTriggered(this.context.pendingCommitId);
    }
    this.context.pendingCommitId = null;
    this.context.commitTimestamp = null;
    this.transitionTo('MONITOR');
  }

  private transitionTo(newState: PresentationState): void {
    this.context.stateHistory.push({
      state: this.context.currentState,
      timestamp: Date.now(),
    });
    this.context.currentState = newState;
  }

  // Public getters

  getContext(): PresentationContext {
    return { ...this.context };
  }

  getCurrentState(): PresentationState {
    return this.context.currentState;
  }

  getAdaptedExposureTime(): number {
    return this.context.adaptedExposureTarget;
  }

  isInQuickCancelWindow(): boolean {
    if (!this.context.commitTimestamp) return false;
    const elapsed = (Date.now() - this.context.commitTimestamp) / 1000;
    return elapsed < this.config.quickCancelWindow;
  }

  /**
   * Get pacing info for UI display
   */
  getPacingInfo(): {
    baseTime: number;
    adaptedTime: number;
    currentTime: number;
    remainingTime: number;
    hesitationFactor: number;
    confidenceFactor: number;
  } {
    const state = this.context.decisionState;
    const baseTime = this.config.baseExposureTime;
    const adaptedTime = this.context.adaptedExposureTarget;
    const currentTime = this.context.currentExposureTime;
    
    return {
      baseTime,
      adaptedTime,
      currentTime,
      remainingTime: Math.max(0, adaptedTime - currentTime),
      hesitationFactor: state?.hesitationScore ?? 0.5,
      confidenceFactor: this.context.confidenceChangeRate,
    };
  }
}

// Factory function for easy instantiation
export function createPresentationController(
  config?: Partial<PresentationConfig>,
  callbacks?: {
    onStateChange?: (context: PresentationContext) => void;
    onCommitTriggered?: (nruIndex: number, triggerId: string) => void;
    onUndoTriggered?: (triggerId: string) => void;
  }
): PresentationController {
  return new PresentationController(config, callbacks);
}
