import React from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogTrigger } from '@/components/ui/dialog';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import {
  HelpCircle,
  BookOpen,
  PlayCircle,
  Settings,
  RotateCcw,
  CheckCircle,
} from 'lucide-react';

import HelpSystem from './HelpSystem';
import OnboardingWizard from './OnboardingWizard';
import InteractiveTutorial, {
  tutorialDefinitions,
} from './InteractiveTutorial';
import { ContextualHelpProvider } from './ContextualHelp';
import { useHelpSystem } from './useHelpSystem';

interface HelpSystemIntegrationProps {
  children: React.ReactNode;
}

const HelpSystemIntegration: React.FC<HelpSystemIntegrationProps> = ({
  children,
}) => {
  const {
    config,
    isOnboardingOpen,
    activeTutorial,
    completedTutorials,
    showHelpSystem,
    openOnboarding,
    closeOnboarding,
    completeOnboarding,
    startTutorial,
    completeTutorial,
    closeTutorial,
    toggleHelpSystem,
    resetHelpSystem,
    shouldShowOnboarding,
    getTutorialStatus,
    getCompletionPercentage,
  } = useHelpSystem();

  const activeTutorialData = activeTutorial
    ? tutorialDefinitions.find((t) => t.id === activeTutorial)
    : null;

  const completionPercentage = getCompletionPercentage(
    tutorialDefinitions.length
  );

  return (
    <ContextualHelpProvider>
      {children}

      {/* Help System Floating Button */}
      <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2">
        {/* Tutorial Progress Indicator */}
        {completedTutorials.size > 0 && (
          <div className="bg-white rounded-full shadow-lg p-2 border">
            <div className="flex items-center gap-2 text-sm">
              <CheckCircle className="w-4 h-4 text-green-500" />
              <span className="font-medium">
                {Math.round(completionPercentage)}%
              </span>
            </div>
          </div>
        )}

        {/* Main Help Button */}
        <Popover>
          <PopoverTrigger asChild>
            <Button
              size="lg"
              className="rounded-full w-14 h-14 shadow-lg hover:shadow-xl transition-shadow"
              variant="default"
            >
              <HelpCircle className="w-6 h-6" />
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-80" align="end">
            <div className="space-y-4">
              <div className="text-center">
                <h3 className="font-semibold mb-1">Need Help?</h3>
                <p className="text-sm text-muted-foreground">
                  Access tutorials, documentation, and contextual help
                </p>
              </div>

              <div className="space-y-2">
                <Button
                  variant="outline"
                  className="w-full justify-start"
                  onClick={toggleHelpSystem}
                >
                  <BookOpen className="w-4 h-4 mr-2" />
                  Open Help Center
                </Button>

                <Button
                  variant="outline"
                  className="w-full justify-start"
                  onClick={openOnboarding}
                >
                  <PlayCircle className="w-4 h-4 mr-2" />
                  Getting Started
                </Button>

                <Button
                  variant="outline"
                  className="w-full justify-start"
                  onClick={() => startTutorial('first-semantic-graph')}
                >
                  <PlayCircle className="w-4 h-4 mr-2" />
                  Quick Tutorial
                </Button>
              </div>

              {/* Tutorial Progress */}
              {completedTutorials.size > 0 && (
                <div className="border-t pt-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium">
                      Tutorial Progress
                    </span>
                    <Badge variant="outline">
                      {completedTutorials.size}/{tutorialDefinitions.length}
                    </Badge>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${completionPercentage}%` }}
                    />
                  </div>
                </div>
              )}

              {/* Quick Actions */}
              <div className="border-t pt-3 space-y-2">
                <Button
                  variant="ghost"
                  size="sm"
                  className="w-full justify-start text-muted-foreground"
                  onClick={resetHelpSystem}
                >
                  <RotateCcw className="w-3 h-3 mr-2" />
                  Reset Help System
                </Button>
              </div>
            </div>
          </PopoverContent>
        </Popover>
      </div>

      {/* Onboarding Wizard */}
      <OnboardingWizard
        isOpen={shouldShowOnboarding()}
        onClose={closeOnboarding}
        onComplete={completeOnboarding}
      />

      {/* Interactive Tutorial */}
      {activeTutorialData && (
        <InteractiveTutorial
          tutorial={activeTutorialData}
          isOpen={!!activeTutorial}
          onClose={closeTutorial}
          onComplete={completeTutorial}
        />
      )}

      {/* Help System Dialog */}
      <Dialog open={showHelpSystem} onOpenChange={toggleHelpSystem}>
        <DialogContent className="max-w-7xl max-h-[90vh] overflow-hidden p-0">
          <HelpSystem />
        </DialogContent>
      </Dialog>

      {/* Keyboard Shortcut Handler */}
      <KeyboardShortcuts
        onOpenHelp={toggleHelpSystem}
        onOpenOnboarding={openOnboarding}
        onStartQuickTutorial={() => startTutorial('first-semantic-graph')}
      />
    </ContextualHelpProvider>
  );
};

// Keyboard shortcuts component
const KeyboardShortcuts: React.FC<{
  onOpenHelp: () => void;
  onOpenOnboarding: () => void;
  onStartQuickTutorial: () => void;
}> = ({ onOpenHelp, onOpenOnboarding, onStartQuickTutorial }) => {
  React.useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Help system shortcuts
      if (event.key === '?' && !event.ctrlKey && !event.metaKey) {
        event.preventDefault();
        onOpenHelp();
      }

      // Onboarding shortcut (Ctrl/Cmd + Shift + ?)
      if (
        event.key === '?' &&
        (event.ctrlKey || event.metaKey) &&
        event.shiftKey
      ) {
        event.preventDefault();
        onOpenOnboarding();
      }

      // Quick tutorial shortcut (Ctrl/Cmd + Shift + T)
      if (
        event.key === 'T' &&
        (event.ctrlKey || event.metaKey) &&
        event.shiftKey
      ) {
        event.preventDefault();
        onStartQuickTutorial();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onOpenHelp, onOpenOnboarding, onStartQuickTutorial]);

  return null;
};

// Help System Status Component (for debugging/admin)
export const HelpSystemStatus: React.FC = () => {
  const { config, completedTutorials, getCompletionPercentage } =
    useHelpSystem();

  return (
    <div className="p-4 bg-gray-50 rounded-lg text-sm">
      <h4 className="font-semibold mb-2">Help System Status</h4>
      <div className="space-y-1">
        <div>Onboarding: {config.showOnboarding ? 'Enabled' : 'Disabled'}</div>
        <div>
          Contextual Help:{' '}
          {config.enableContextualHelp ? 'Enabled' : 'Disabled'}
        </div>
        <div>
          Completed Tutorials: {completedTutorials.size}/
          {tutorialDefinitions.length}
        </div>
        <div>
          Progress:{' '}
          {Math.round(getCompletionPercentage(tutorialDefinitions.length))}%
        </div>
        <div>User Role: {config.userPreferences.role || 'Not set'}</div>
        <div>Experience: {config.userPreferences.experience || 'Not set'}</div>
      </div>
    </div>
  );
};

export default HelpSystemIntegration;
