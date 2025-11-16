// Help System Components
export { default as HelpSystem } from './HelpSystem';
export {
  default as ContextualHelp,
  ContextualHelpProvider,
  HelpIcon,
  QuickHelp,
  useContextualHelp,
} from './ContextualHelp';
export {
  default as InteractiveTutorial,
  tutorialDefinitions,
} from './InteractiveTutorial';
export { default as OnboardingWizard } from './OnboardingWizard';
export { default as BestPracticesGuide } from './BestPracticesGuide';

// Help System Types
export interface HelpSystemConfig {
  showOnboarding: boolean;
  enableContextualHelp: boolean;
  tutorialProgress: Record<string, boolean>;
  userPreferences: {
    role: string;
    experience: string;
    interests: string[];
  };
}

// Help System Hooks
export { useHelpSystem } from './useHelpSystem';
