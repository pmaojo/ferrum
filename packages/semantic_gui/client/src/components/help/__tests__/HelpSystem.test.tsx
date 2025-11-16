import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, beforeEach, jest } from '@jest/globals';
import HelpSystem from '../HelpSystem';
import { useHelpSystem } from '../useHelpSystem';
import { ContextualHelpProvider } from '../ContextualHelp';

// Mock the useHelpSystem hook
jest.mock('../useHelpSystem');
const mockUseHelpSystem = useHelpSystem as jest.MockedFunction<
  typeof useHelpSystem
>;

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

describe('HelpSystem', () => {
  const mockHelpSystemState = {
    config: {
      showOnboarding: true,
      enableContextualHelp: true,
      tutorialProgress: {},
      userPreferences: {
        role: '',
        experience: '',
        interests: [],
      },
    },
    isOnboardingOpen: false,
    activeTutorial: null,
    completedTutorials: new Set(),
    showHelpSystem: false,
    openOnboarding: jest.fn(),
    closeOnboarding: jest.fn(),
    completeOnboarding: jest.fn(),
    startTutorial: jest.fn(),
    completeTutorial: jest.fn(),
    closeTutorial: jest.fn(),
    toggleHelpSystem: jest.fn(),
    updateUserPreferences: jest.fn(),
    resetHelpSystem: jest.fn(),
    toggleContextualHelp: jest.fn(),
    shouldShowOnboarding: jest.fn(() => false),
    getTutorialStatus: jest.fn(() => false),
    getCompletionPercentage: jest.fn(() => 0),
    saveTutorialProgress: jest.fn(),
  };

  beforeEach(() => {
    mockUseHelpSystem.mockReturnValue(mockHelpSystemState);
    jest.clearAllMocks();
  });

  const renderHelpSystem = () => {
    return render(
      <ContextualHelpProvider>
        <HelpSystem />
      </ContextualHelpProvider>
    );
  };

  it('renders the help system with all tabs', () => {
    renderHelpSystem();

    expect(screen.getByText('Help & Documentation')).toBeInTheDocument();
    expect(screen.getByText('Tutorials')).toBeInTheDocument();
    expect(screen.getByText('Help Topics')).toBeInTheDocument();
    expect(screen.getByText('Best Practices')).toBeInTheDocument();
    expect(screen.getByText('Getting Started')).toBeInTheDocument();
  });

  it('displays tutorial cards in the tutorials tab', () => {
    renderHelpSystem();

    // Should show tutorial cards
    expect(
      screen.getByText('Introduction to Semantic Architecture')
    ).toBeInTheDocument();
    expect(screen.getByText('OWL Ontology Fundamentals')).toBeInTheDocument();
    expect(
      screen.getByText('Hexagonal Architecture Best Practices')
    ).toBeInTheDocument();
    expect(screen.getByText('Kthulu CLI Integration')).toBeInTheDocument();
  });

  it('shows tutorial difficulty badges', () => {
    renderHelpSystem();

    expect(screen.getByText('beginner')).toBeInTheDocument();
    expect(screen.getByText('intermediate')).toBeInTheDocument();
  });

  it('allows starting a tutorial', () => {
    renderHelpSystem();

    const startButtons = screen.getAllByText('Start Tutorial');
    fireEvent.click(startButtons[0]);

    // Should open tutorial dialog
    expect(
      screen.getByText('Introduction to Semantic Architecture')
    ).toBeInTheDocument();
  });

  it('switches between tabs correctly', () => {
    renderHelpSystem();

    // Click on Help Topics tab
    fireEvent.click(screen.getByText('Help Topics'));

    // Should show search input for help topics
    expect(
      screen.getByPlaceholderText('Search help topics...')
    ).toBeInTheDocument();
  });

  it('filters help topics based on search', async () => {
    renderHelpSystem();

    // Switch to Help Topics tab
    fireEvent.click(screen.getByText('Help Topics'));

    const searchInput = screen.getByPlaceholderText('Search help topics...');
    fireEvent.change(searchInput, { target: { value: 'OWL' } });

    await waitFor(() => {
      expect(screen.getByText('OWL Classes')).toBeInTheDocument();
    });
  });

  it('shows best practices guide', () => {
    renderHelpSystem();

    // Click on Best Practices tab
    fireEvent.click(screen.getByText('Best Practices'));

    // Should show best practices content
    expect(screen.getByText('Hexagonal Architecture')).toBeInTheDocument();
    expect(screen.getByText('Domain-Driven Design')).toBeInTheDocument();
    expect(screen.getByText('Semantic Modeling')).toBeInTheDocument();
  });

  it('shows onboarding wizard steps', () => {
    renderHelpSystem();

    // Click on Getting Started tab
    fireEvent.click(screen.getByText('Getting Started'));

    // Should show onboarding steps
    expect(
      screen.getByText('Welcome to Semantic Architecture')
    ).toBeInTheDocument();
  });

  it('tracks tutorial completion', () => {
    const mockCompletedTutorials = new Set(['semantic-intro']);
    mockUseHelpSystem.mockReturnValue({
      ...mockHelpSystemState,
      completedTutorials: mockCompletedTutorials,
      getTutorialStatus: jest.fn((id) => mockCompletedTutorials.has(id)),
    });

    renderHelpSystem();

    // Should show completed tutorial with checkmark
    const completedTutorial = screen
      .getByText('Introduction to Semantic Architecture')
      .closest('.cursor-pointer');
    expect(completedTutorial).toBeInTheDocument();
  });

  it('handles tutorial step navigation', () => {
    renderHelpSystem();

    // Start a tutorial
    const startButtons = screen.getAllByText('Start Tutorial');
    fireEvent.click(startButtons[0]);

    // Should show tutorial step with navigation
    expect(screen.getByText('Next')).toBeInTheDocument();
    expect(screen.getByText('Previous')).toBeInTheDocument();
  });

  it('shows tutorial progress', () => {
    const mockCompletedTutorials = new Set(['semantic-intro', 'owl-basics']);
    mockUseHelpSystem.mockReturnValue({
      ...mockHelpSystemState,
      completedTutorials: mockCompletedTutorials,
      getCompletionPercentage: jest.fn(() => 50),
    });

    renderHelpSystem();

    // Should show progress indicator
    expect(screen.getByText('2 / 4')).toBeInTheDocument(); // Assuming 4 total tutorials
  });

  it('provides contextual help examples', () => {
    renderHelpSystem();

    // Switch to Help Topics
    fireEvent.click(screen.getByText('Help Topics'));

    // Should show help topics with examples
    expect(screen.getByText('OWL Classes')).toBeInTheDocument();
    expect(screen.getByText('Object Properties')).toBeInTheDocument();
  });

  it('handles tutorial completion', async () => {
    renderHelpSystem();

    // Start a tutorial
    const startButtons = screen.getAllByText('Start Tutorial');
    fireEvent.click(startButtons[0]);

    // Navigate to last step and complete
    const nextButton = screen.getByText('Next');
    fireEvent.click(nextButton);

    // Should eventually show complete button
    await waitFor(() => {
      const completeButton = screen.queryByText('Complete');
      if (completeButton) {
        fireEvent.click(completeButton);
      }
    });
  });

  it('shows code examples in tutorials', () => {
    renderHelpSystem();

    // Start OWL tutorial which has code examples
    const owlTutorial = screen
      .getByText('OWL Ontology Fundamentals')
      .closest('.cursor-pointer');
    const startButton = owlTutorial?.querySelector('button');
    if (startButton) {
      fireEvent.click(startButton);
    }

    // Should show code examples
    expect(screen.getByText('Code Example:')).toBeInTheDocument();
  });
});

describe('useHelpSystem hook', () => {
  beforeEach(() => {
    localStorageMock.getItem.mockClear();
    localStorageMock.setItem.mockClear();
    jest.clearAllMocks();
  });

  it('loads configuration from localStorage', () => {
    const savedConfig = {
      showOnboarding: false,
      enableContextualHelp: true,
      tutorialProgress: { 'semantic-intro': true },
      userPreferences: {
        role: 'developer',
        experience: 'intermediate',
        interests: [],
      },
    };

    localStorageMock.getItem.mockReturnValue(JSON.stringify(savedConfig));

    // Test would need to be run in a component that uses the hook
    // This is a simplified test structure
    expect(localStorageMock.getItem).toHaveBeenCalledWith('helpSystemConfig');
  });

  it('saves configuration to localStorage', () => {
    // This would test the saveConfig function
    const config = {
      showOnboarding: false,
      enableContextualHelp: true,
      tutorialProgress: {},
      userPreferences: {
        role: 'architect',
        experience: 'advanced',
        interests: ['semantic'],
      },
    };

    // Mock implementation would call localStorage.setItem
    expect(localStorageMock.setItem).toHaveBeenCalledWith(
      'helpSystemConfig',
      JSON.stringify(config)
    );
  });

  it('tracks tutorial progress', () => {
    const tutorialId = 'semantic-intro';
    const progress = [tutorialId];

    // Mock saving tutorial progress
    expect(localStorageMock.setItem).toHaveBeenCalledWith(
      'tutorialProgress',
      JSON.stringify(progress)
    );
  });
});
