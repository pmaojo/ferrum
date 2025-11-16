import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { HelpIcon, QuickHelp, useContextualHelp } from '../ContextualHelp';
import { useHelpSystem } from '../useHelpSystem';

/**
 * Example: Graph Editor component enhanced with contextual help
 * This shows how to integrate help system into existing components
 */
const GraphEditorWithHelp: React.FC = () => {
  const { showHelp } = useContextualHelp();
  const { startTutorial, getTutorialStatus } = useHelpSystem();

  const handleAddNode = (nodeType: string) => {
    // Your existing node creation logic
    console.log(`Adding ${nodeType} node`);

    // Show contextual help for first-time users
    if (!getTutorialStatus('first-semantic-graph')) {
      showHelp(`${nodeType.toLowerCase()}-concepts`);
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header with help integration */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-bold">Semantic Graph Editor</h1>
          <HelpIcon contentId="semantic-reasoning" />
        </div>

        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => startTutorial('first-semantic-graph')}
          >
            Start Tutorial
          </Button>
          <QuickHelp
            title="Graph Editor Help"
            content="Create and edit your semantic architecture graph. Add nodes, connect relationships, and validate your design."
          >
            <Button variant="ghost" size="sm">
              Help
            </Button>
          </QuickHelp>
        </div>
      </div>

      {/* Toolbar with contextual help */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            Add Components
            <HelpIcon contentId="owl-classes" size="sm" />
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <NodeButton
              type="Module"
              description="Bounded context or domain module"
              helpId="bounded-contexts"
              onClick={() => handleAddNode('Module')}
              testId="add-module-button"
            />

            <NodeButton
              type="UseCase"
              description="Business operation or service"
              helpId="use-cases"
              onClick={() => handleAddNode('UseCase')}
              testId="add-usecase-button"
            />

            <NodeButton
              type="Port"
              description="Interface or contract"
              helpId="ports-adapters"
              onClick={() => handleAddNode('Port')}
              testId="add-port-button"
            />

            <NodeButton
              type="Adapter"
              description="Infrastructure implementation"
              helpId="ports-adapters"
              onClick={() => handleAddNode('Adapter')}
              testId="add-adapter-button"
            />
          </div>
        </CardContent>
      </Card>

      {/* Validation Panel with help */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            Architecture Validation
            <HelpIcon contentId="validation-rules" size="sm" />
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <ValidationRule
              title="Dependency Inversion Principle"
              status="passing"
              helpId="dependency-inversion"
              description="Domain components should not depend on infrastructure"
            />

            <ValidationRule
              title="Bounded Context Integrity"
              status="warning"
              helpId="bounded-contexts"
              description="Entities should not cross context boundaries"
            />

            <ValidationRule
              title="Port Implementation"
              status="failing"
              helpId="ports-adapters"
              description="All ports should have at least one adapter"
            />
          </div>
        </CardContent>
      </Card>

      {/* Graph Canvas Placeholder */}
      <Card className="min-h-[400px]">
        <CardContent className="p-6">
          <div
            className="w-full h-full border-2 border-dashed border-gray-300 rounded-lg flex items-center justify-center"
            data-testid="graph-editor"
          >
            <div className="text-center space-y-2">
              <p className="text-muted-foreground">
                Your semantic graph will appear here
              </p>
              <Button
                variant="outline"
                onClick={() => startTutorial('first-semantic-graph')}
              >
                Start with Tutorial
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

// Helper component for node buttons with integrated help
const NodeButton: React.FC<{
  type: string;
  description: string;
  helpId: string;
  onClick: () => void;
  testId: string;
}> = ({ type, description, helpId, onClick, testId }) => {
  return (
    <div className="relative">
      <Button
        variant="outline"
        className="w-full h-auto p-4 flex flex-col items-center gap-2"
        onClick={onClick}
        data-testid={testId}
      >
        <div className="text-lg font-semibold">{type}</div>
        <div className="text-xs text-muted-foreground text-center">
          {description}
        </div>
      </Button>
      <div className="absolute top-2 right-2">
        <HelpIcon contentId={helpId} size="sm" variant="icon" />
      </div>
    </div>
  );
};

// Helper component for validation rules with help
const ValidationRule: React.FC<{
  title: string;
  status: 'passing' | 'warning' | 'failing';
  helpId: string;
  description: string;
}> = ({ title, status, helpId, description }) => {
  const statusColors = {
    passing: 'text-green-600 bg-green-50 border-green-200',
    warning: 'text-yellow-600 bg-yellow-50 border-yellow-200',
    failing: 'text-red-600 bg-red-50 border-red-200',
  };

  const statusIcons = {
    passing: '✓',
    warning: '⚠',
    failing: '✗',
  };

  return (
    <div className={`p-3 rounded-lg border ${statusColors[status]}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-lg">{statusIcons[status]}</span>
          <div>
            <div className="font-medium">{title}</div>
            <div className="text-sm opacity-75">{description}</div>
          </div>
        </div>
        <HelpIcon contentId={helpId} size="sm" />
      </div>
    </div>
  );
};

export default GraphEditorWithHelp;
