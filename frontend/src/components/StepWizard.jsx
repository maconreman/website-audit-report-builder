import React from 'react'

export default function StepWizard({ steps, currentStep, completedSteps, onStepClick, isProcessing }) {
  return (
    <div className="step-bar">
      <div className="step-bar-inner">
        {steps.map((step) => {
          const isActive = step.id === currentStep
          const isComplete = completedSteps.includes(step.id)
          const maxAllowed = Math.max(1, ...completedSteps, 0) + 1
          const isClickable = !isProcessing && step.id <= maxAllowed

          let cls = 'step-bar-item'
          if (isActive) cls += ' active'
          if (isComplete) cls += ' complete'
          if (isClickable) cls += ' clickable'

          return (
            <div
              key={step.id}
              className={cls}
              onClick={() => isClickable && onStepClick(step.id)}
            >
              <span className="step-num">
                {isComplete && !isActive ? (
                  <svg width="11" height="11" viewBox="0 0 16 16" fill="none">
                    <path d="M3 8.5L6.5 12L13 4" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                ) : step.id}
              </span>
              <span>{step.label}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
