# Help System Documentation

## Overview

The Help System provides comprehensive documentation, interactive tutorials, and contextual help for users learning semantic architecture with hexagonal design principles. It integrates seamlessly with the SCG application to provide just-in-time learning and guidance.

## Components

### 1. HelpSystem (Main Interface)

- **Purpose**: Central hub for all help content
- **Features**:
  - Tabbed interface with tutorials, help topics, best practices, and onboarding
  - Search functionality for help topics
  - Progress tracking for tutorials
  - Interactive tutorial launcher

### 2. ContextualHelp

- **Purpose**: Provides contextual help throughout the application
- **Features**:
  - Help icons that can be placed next to UI elements
  - Popover quick help for immediate assistance
  - Modal detailed help for complex topics
  - Context-aware help content based on current user action

### 3. InteractiveTutorial

- **Purpose**: Step-by-step guided tutorials with interactive elements
- **Features**:
  - Element highlighting and guided interactions
  - Progress tracking and validation
  - Code examples and tips
  - Branching tutorial paths based on user actions

### 4. OnboardingWizard

- **Purpose**: First-time user experience and setup
- **Features**:
  - User profiling (role, experience level, interests)
  - System configuration and preferences
  - Agent setup and configuration
  - Quick tour of main features

### 5. BestPracticesGuide

- **Purpose**: Comprehensive guide to architectural best practices
- **Features**:
  - Categorized practices (Hexagonal, DDD, Semantic, SOLID, Testing)
  - Code examples with good/bad patterns
  - Implementation tips and common mistakes
  - Related principles and cross-references

## Integration

### Adding to Your Application

```tsx
import { HelpSystemIntegration } from '@/components/help';

function App() {
  return (
    <HelpSystemIntegration>
      {/* Your application content */}
      <YourMainComponent />
    </HelpSystemIntegration>
  );
}
```

### Using Contextual Help

```tsx
import { HelpIcon, QuickHelp } from '@/components/help';

function MyComponent() {
  return (
    <div className="flex items-center gap-2">
      <label>OWL Classes</label>
      <HelpIcon contentId="owl-classes" />

      <QuickHelp
        title="Quick Tip"
        content="Classes represent concepts in your domain"
      >
        <Button variant="ghost">?</Button>
      </QuickHelp>
    </div>
  );
}
```

### Managing Help State

```tsx
import { useHelpSystem } from '@/components/help';

function MyComponent() {
  const {
    startTutorial,
    openOnboarding,
    getTutorialStatus,
    completedTutorials,
  } = useHelpSystem();

  return (
    <div>
      <Button onClick={() => startTutorial('owl-basics')}>
        Start OWL Tutorial
      </Button>

      {getTutorialStatus('first-semantic-graph') && (
        <Badge>Tutorial Completed</Badge>
      )}
    </div>
  );
}
```

## Documentation Flow

SCG coordinates the movement of requirement documentation from Kthulu into the
PermaGraph knowledge graph. When users choose to refresh documentation, the
client calls the `/api/v1/docs-ingest` endpoint. The server forwards the request
to PermaGraph's `/api/v1/docs-ingest` service, which validates and stores the
documents in its semantic ontology. This flow keeps requirements in sync and
available for reasoning across the platform.

## Content Management

### Adding New Help Topics

1. **Contextual Help Content**: Add to `helpContent` object in `ContextualHelp.tsx`
2. **Tutorial Definitions**: Add to `tutorialDefinitions` array in `InteractiveTutorial.tsx`
3. **Best Practices**: Add to `bestPractices` array in `BestPracticesGuide.tsx`

### Help Content Structure

```typescript
interface HelpContent {
  id: string;
  title: string;
  description: string;
  content: string;
  category: 'owl' | 'architecture' | 'semantic' | 'kthulu' | 'ui';
  examples?: string[];
  relatedTopics?: string[];
  externalLinks?: { title: string; url: string }[];
}
```

### Tutorial Structure

```typescript
interface Tutorial {
  id: string;
  title: string;
  description: string;
  category: 'getting-started' | 'semantic' | 'architecture' | 'advanced';
  estimatedTime: string;
  prerequisites?: string[];
  steps: TutorialStep[];
}
```

## Keyboard Shortcuts

- **?**: Open help system
- **Ctrl/Cmd + Shift + ?**: Open onboarding wizard
- **Ctrl/Cmd + Shift + T**: Start quick tutorial

## Customization

### Theming

The help system uses the same design system as the main application. Customize colors and styling through CSS variables or Tailwind configuration.

### Content Localization

Help content can be localized by creating language-specific content objects and switching based on user locale.

### Analytics Integration

Track help system usage by adding analytics calls to key actions:

```typescript
// Example analytics integration
const { startTutorial } = useHelpSystem();

const handleStartTutorial = (tutorialId: string) => {
  analytics.track('tutorial_started', { tutorial_id: tutorialId });
  startTutorial(tutorialId);
};
```

## Best Practices

### Content Writing

1. **Be Concise**: Keep explanations focused and actionable
2. **Use Examples**: Provide concrete code examples and use cases
3. **Progressive Disclosure**: Start simple, add complexity gradually
4. **Visual Aids**: Use diagrams and screenshots where helpful

### User Experience

1. **Non-Intrusive**: Help should be available but not overwhelming
2. **Contextual**: Show relevant help based on current user context
3. **Progressive**: Guide users from basic to advanced concepts
4. **Searchable**: Make content easily discoverable

### Maintenance

1. **Keep Updated**: Regularly review and update content
2. **User Feedback**: Collect and act on user feedback
3. **Analytics**: Monitor usage patterns to improve content
4. **Testing**: Test tutorials and interactive elements regularly

## Troubleshooting

### Common Issues

1. **Tutorial Steps Not Highlighting Elements**
   - Check CSS selectors in tutorial step definitions
   - Ensure target elements have correct `data-testid` attributes
   - Verify element exists when tutorial step runs

2. **Help Content Not Loading**
   - Check for JavaScript errors in console
   - Verify help content IDs match between components
   - Ensure localStorage is available for progress tracking

3. **Onboarding Not Showing**
   - Check localStorage for existing configuration
   - Verify `showOnboarding` flag in user preferences
   - Clear localStorage to reset onboarding state

### Debug Mode

Enable debug mode to see help system internals:

```tsx
import { HelpSystemStatus } from '@/components/help';

// Add to your admin/debug panel
<HelpSystemStatus />;
```

## Future Enhancements

1. **AI-Powered Help**: Use LLM to generate contextual explanations
2. **Video Tutorials**: Integrate video content for complex topics
3. **Community Content**: Allow users to contribute help content
4. **Adaptive Learning**: Personalize content based on user behavior
5. **Multi-language Support**: Localize content for international users

## Cómo añadir plantilla

1. Copia un archivo de plantilla existente en `templates/semantic_gui` y renómbralo.
2. Actualiza los campos `id` y `name` dentro del archivo copiado.
3. Define el bloque `cli` con el comando binario y las operaciones necesarias.
4. Reinicia el servidor para que `useTemplates()` detecte la nueva plantilla.
