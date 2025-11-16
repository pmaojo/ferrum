import { useState, useEffect, useCallback } from 'react';
import { HelpSystemConfig } from './index';

interface HelpSystemState {
  config: HelpSystemConfig;
  isOnboardingOpen: boolean;
  activeTutorial: string | null;
  completedTutorials: Set<string>;
  showHelpSystem: boolean;
}

const DEFAULT_CONFIG: HelpSystemConfig = {
  showOnboarding: true,
  enableContextualHelp: true,
  tutorialProgress: {},
  userPreferences: {
    role: '',
    experience: '',
    interests: [],
  },
};

export const useHelpSystem = () => {
  const [state, setState] = useState<HelpSystemState>({
    config: DEFAULT_CONFIG,
    isOnboardingOpen: false,
    activeTutorial: null,
    completedTutorials: new Set(),
    showHelpSystem: false,
  });

  // Load help system configuration from localStorage
  useEffect(() => {
    const savedConfig = localStorage.getItem('helpSystemConfig');
    const savedProgress = localStorage.getItem('tutorialProgress');

    if (savedConfig) {
      try {
        const config = JSON.parse(savedConfig);
        setState((prev) => ({ ...prev, config }));
      } catch (error) {
        console.warn('Failed to load help system config:', error);
      }
    }

    if (savedProgress) {
      try {
        const progress = JSON.parse(savedProgress);
        setState((prev) => ({
          ...prev,
          completedTutorials: new Set(progress),
          config: { ...prev.config, tutorialProgress: progress },
        }));
      } catch (error) {
        console.warn('Failed to load tutorial progress:', error);
      }
    }

    // Check if user is new (no saved config) and should see onboarding
    if (!savedConfig) {
      setState((prev) => ({ ...prev, isOnboardingOpen: true }));
    }
  }, []);

  // Save configuration to localStorage
  const saveConfig = useCallback((config: HelpSystemConfig) => {
    localStorage.setItem('helpSystemConfig', JSON.stringify(config));
    setState((prev) => ({ ...prev, config }));
  }, []);

  // Save tutorial progress
  const saveTutorialProgress = useCallback(
    (tutorialId: string, completed: boolean) => {
      setState((prev) => {
        const newCompleted = new Set(prev.completedTutorials);
        const newProgress = { ...prev.config.tutorialProgress };

        if (completed) {
          newCompleted.add(tutorialId);
          newProgress[tutorialId] = true;
        } else {
          newCompleted.delete(tutorialId);
          delete newProgress[tutorialId];
        }

        const newConfig = { ...prev.config, tutorialProgress: newProgress };

        localStorage.setItem(
          'tutorialProgress',
          JSON.stringify(Array.from(newCompleted))
        );
        localStorage.setItem('helpSystemConfig', JSON.stringify(newConfig));

        return {
          ...prev,
          completedTutorials: newCompleted,
          config: newConfig,
        };
      });
    },
    []
  );

  // Open onboarding wizard
  const openOnboarding = useCallback(() => {
    setState((prev) => ({ ...prev, isOnboardingOpen: true }));
  }, []);

  // Close onboarding wizard
  const closeOnboarding = useCallback(() => {
    setState((prev) => ({ ...prev, isOnboardingOpen: false }));
  }, []);

  // Complete onboarding
  const completeOnboarding = useCallback(() => {
    const newConfig = { ...state.config, showOnboarding: false };
    saveConfig(newConfig);
    setState((prev) => ({ ...prev, isOnboardingOpen: false }));
  }, [state.config, saveConfig]);

  // Start tutorial
  const startTutorial = useCallback((tutorialId: string) => {
    setState((prev) => ({ ...prev, activeTutorial: tutorialId }));
  }, []);

  // Complete tutorial
  const completeTutorial = useCallback(
    (tutorialId: string) => {
      saveTutorialProgress(tutorialId, true);
      setState((prev) => ({ ...prev, activeTutorial: null }));
    },
    [saveTutorialProgress]
  );

  // Close tutorial
  const closeTutorial = useCallback(() => {
    setState((prev) => ({ ...prev, activeTutorial: null }));
  }, []);

  // Toggle help system visibility
  const toggleHelpSystem = useCallback(() => {
    setState((prev) => ({ ...prev, showHelpSystem: !prev.showHelpSystem }));
  }, []);

  // Update user preferences
  const updateUserPreferences = useCallback(
    (preferences: Partial<HelpSystemConfig['userPreferences']>) => {
      const newConfig = {
        ...state.config,
        userPreferences: { ...state.config.userPreferences, ...preferences },
      };
      saveConfig(newConfig);
    },
    [state.config, saveConfig]
  );

  // Check if user should see onboarding
  const shouldShowOnboarding = useCallback(() => {
    return state.config.showOnboarding && state.isOnboardingOpen;
  }, [state.config.showOnboarding, state.isOnboardingOpen]);

  // Get tutorial completion status
  const getTutorialStatus = useCallback(
    (tutorialId: string) => {
      return state.completedTutorials.has(tutorialId);
    },
    [state.completedTutorials]
  );

  // Get completion percentage
  const getCompletionPercentage = useCallback(
    (totalTutorials: number) => {
      return (state.completedTutorials.size / totalTutorials) * 100;
    },
    [state.completedTutorials]
  );

  // Reset help system (for testing or user request)
  const resetHelpSystem = useCallback(() => {
    localStorage.removeItem('helpSystemConfig');
    localStorage.removeItem('tutorialProgress');
    setState({
      config: DEFAULT_CONFIG,
      isOnboardingOpen: true,
      activeTutorial: null,
      completedTutorials: new Set(),
      showHelpSystem: false,
    });
  }, []);

  // Enable/disable contextual help
  const toggleContextualHelp = useCallback(() => {
    const newConfig = {
      ...state.config,
      enableContextualHelp: !state.config.enableContextualHelp,
    };
    saveConfig(newConfig);
  }, [state.config, saveConfig]);

  return {
    // State
    config: state.config,
    isOnboardingOpen: state.isOnboardingOpen,
    activeTutorial: state.activeTutorial,
    completedTutorials: state.completedTutorials,
    showHelpSystem: state.showHelpSystem,

    // Actions
    openOnboarding,
    closeOnboarding,
    completeOnboarding,
    startTutorial,
    completeTutorial,
    closeTutorial,
    toggleHelpSystem,
    updateUserPreferences,
    resetHelpSystem,
    toggleContextualHelp,

    // Utilities
    shouldShowOnboarding,
    getTutorialStatus,
    getCompletionPercentage,
    saveTutorialProgress,
  };
};
