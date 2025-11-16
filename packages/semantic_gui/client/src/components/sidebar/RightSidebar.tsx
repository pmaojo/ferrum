import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useUpdateNode, useDeleteNode } from '@/hooks/use-graph';
import { useToast } from '@/hooks/use-toast';
import { ExternalLink, Save, Copy, Trash2, Bot } from 'lucide-react';
import { TemplateRuleValidator } from '../TemplateRuleValidator';
import type { Node, Edge } from 'reactflow';
import type { GraphNodeData } from '@/types/graph';

interface RightSidebarProps {
  selectedNode: Node<GraphNodeData> | null;
  onNodeUpdate: (nodeId: string, updates: Partial<GraphNodeData>) => void;
  allNodes?: Node<GraphNodeData>[];
  allEdges?: Edge[];
  template?: any;
}

export function RightSidebar({
  selectedNode,
  onNodeUpdate,
  allNodes = [],
  allEdges = [],
  template,
}: RightSidebarProps) {
  const updateNodeMutation = useUpdateNode();
  const deleteNodeMutation = useDeleteNode();
  const { toast } = useToast();
  const [aiInput, setAiInput] = useState('');

  const [formData, setFormData] = useState<Partial<GraphNodeData>>({});

  // Update form data when selected node changes
  useEffect(() => {
    if (selectedNode) {
      setFormData({
        name: selectedNode.data.name,
        type: selectedNode.data.type,
        filePath: selectedNode.data.filePath,
        description: selectedNode.data.description,
      });
    } else {
      setFormData({});
    }
  }, [selectedNode]);

  const handleSave = () => {
    if (!selectedNode) return;

    updateNodeMutation.mutate(
      {
        id: selectedNode.id,
        data: {
          name: formData.name,
          type: formData.type,
          filePath: formData.filePath,
          description: formData.description,
        },
      },
      {
        onSuccess: () => {
          toast({
            title: 'Node updated',
            description: 'Node properties have been saved.',
          });
          onNodeUpdate(selectedNode.id, formData);
        },
        onError: () => {
          toast({
            title: 'Error',
            description: 'Failed to update node.',
            variant: 'destructive',
          });
        },
      }
    );
  };

  const handleDelete = () => {
    if (!selectedNode) return;

    deleteNodeMutation.mutate(selectedNode.id, {
      onSuccess: () => {
        toast({
          title: 'Node deleted',
          description: 'Node has been removed from the graph.',
        });
      },
      onError: () => {
        toast({
          title: 'Error',
          description: 'Failed to delete node.',
          variant: 'destructive',
        });
      },
    });
  };

  const handleDuplicate = () => {
    if (!selectedNode) return;

    // This would create a new node with similar properties
    toast({
      title: 'Duplicate created',
      description: 'A copy of the node has been created.',
    });
  };

  const openInEditor = () => {
    if (selectedNode?.data.filePath) {
      // In a real implementation, this would open the file in the user's editor
      toast({
        title: 'Opening file',
        description: `Would open ${selectedNode.data.filePath} in editor`,
      });
    }
  };

  const handleAiQuestion = () => {
    if (!aiInput.trim()) return;

    // In a real implementation, this would send the question to an AI service
    toast({
      title: 'AI Query',
      description: `Processing: "${aiInput}"`,
    });
    setAiInput('');
  };

  if (!selectedNode) {
    return (
      <div className="w-80 bg-card border-l-2 border-primary flex flex-col hacker-border">
        <div className="p-6">
          <h2 className="text-lg font-black text-primary mb-2 terminal-font hacker-text-glow">
            PROPERTIES
          </h2>
          <p className="text-sm text-primary/60 terminal-font">
            SELECT NODE TO EDIT PROPERTIES
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-80 bg-card border-l-2 border-primary flex flex-col hacker-border">
      {/* BRUTAL HEADER */}
      <div className="p-4 border-b-2 border-primary hacker-border">
        <h2 className="text-lg font-black text-primary terminal-font hacker-text-glow">
          NODE_PROPERTIES
        </h2>
        <p className="text-sm text-primary/70 terminal-font">
          {selectedNode.data.name.toUpperCase()}
        </p>
      </div>

      {/* Properties Form */}
      <div className="flex-1 p-4 space-y-6 overflow-y-auto">
        {/* Basic Properties */}
        <div className="space-y-4">
          <div>
            <Label
              htmlFor="node-type"
              className="text-sm font-black text-primary terminal-font"
            >
              NODE_TYPE
            </Label>
            <Select
              value={formData.type}
              onValueChange={(value) =>
                setFormData((prev) => ({ ...prev, type: value }))
              }
            >
              <SelectTrigger className="bg-input border-2 border-primary text-primary terminal-font hacker-glow">
                <SelectValue placeholder="SELECT_TYPE..." />
              </SelectTrigger>
              <SelectContent className="bg-card border-2 border-primary">
                <SelectItem
                  value="usecase"
                  className="text-primary terminal-font"
                >
                  USE_CASE
                </SelectItem>
                <SelectItem
                  value="adapter"
                  className="text-primary terminal-font"
                >
                  ADAPTER
                </SelectItem>
                <SelectItem
                  value="entity"
                  className="text-primary terminal-font"
                >
                  ENTITY
                </SelectItem>
                <SelectItem
                  value="controller"
                  className="text-primary terminal-font"
                >
                  CONTROLLER
                </SelectItem>
                <SelectItem
                  value="repository"
                  className="text-primary terminal-font"
                >
                  REPOSITORY
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label
              htmlFor="node-name"
              className="text-sm font-black text-primary terminal-font"
            >
              NAME
            </Label>
            <Input
              id="node-name"
              value={formData.name || ''}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, name: e.target.value }))
              }
              placeholder="ENTER_NODE_NAME..."
              className="bg-input border-2 border-primary text-primary terminal-font hacker-glow"
            />
          </div>

          <div>
            <Label
              htmlFor="node-description"
              className="text-sm font-black text-primary terminal-font"
            >
              DESCRIPTION
            </Label>
            <Textarea
              id="node-description"
              value={formData.description || ''}
              onChange={(e) =>
                setFormData((prev) => ({
                  ...prev,
                  description: e.target.value,
                }))
              }
              placeholder="ENTER_DESCRIPTION..."
              rows={3}
              className="bg-input border-2 border-primary text-primary terminal-font hacker-glow"
            />
          </div>

          <div>
            <Label
              htmlFor="node-filepath"
              className="text-sm font-black text-primary terminal-font"
            >
              FILE_PATH
            </Label>
            <div className="flex space-x-2">
              <Input
                id="node-filepath"
                value={formData.filePath || ''}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, filePath: e.target.value }))
                }
                placeholder="src/path/to/file.ts"
                className="terminal-font text-sm bg-input border-2 border-primary text-primary hacker-glow"
              />
              <Button
                variant="outline"
                size="sm"
                onClick={openInEditor}
                className="border-2 border-secondary text-secondary hover:bg-secondary/20 terminal-font"
              >
                <ExternalLink className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>

        {/* Confirmation Status */}
        {formData.filePath && (
          <div className="space-y-2">
            <Label className="text-sm font-black text-primary terminal-font">
              STATUS
            </Label>
            <div
              className={`px-3 py-2 rounded border ${
                selectedNode?.data.metadata?.confirmed
                  ? 'border-green-600 bg-green-900/20 text-green-400'
                  : 'border-yellow-600 bg-yellow-900/20 text-yellow-400'
              } terminal-font`}
            >
              {selectedNode?.data.metadata?.confirmed
                ? '✓ CONFIRMED'
                : '? UNCONFIRMED'}
              {selectedNode?.data.metadata?.confirmed && (
                <div className="text-xs text-green-300/70 mt-1 terminal-font">
                  Detected in codebase
                </div>
              )}
              {!selectedNode?.data.metadata?.confirmed && (
                <div className="text-xs text-yellow-300/70 mt-1 terminal-font">
                  Not yet detected in AST analysis
                </div>
              )}
            </div>
          </div>
        )}

        {/* Metadata */}
        {selectedNode.data.metadata && (
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Metadata</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {selectedNode.data.metadata.linesOfCode && (
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Lines of Code</span>
                  <span className="font-mono">
                    {selectedNode.data.metadata.linesOfCode}
                  </span>
                </div>
              )}
              {selectedNode.data.metadata.complexity && (
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Complexity</span>
                  <Badge
                    variant={
                      selectedNode.data.metadata.complexity === 'High'
                        ? 'destructive'
                        : selectedNode.data.metadata.complexity === 'Medium'
                          ? 'secondary'
                          : 'default'
                    }
                  >
                    {selectedNode.data.metadata.complexity}
                  </Badge>
                </div>
              )}
              {selectedNode.data.metadata.dependencies && (
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Dependencies</span>
                  <span>
                    {selectedNode.data.metadata.dependencies.length || 0}
                  </span>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Template Validation */}
        {template && allNodes.length > 0 && (
          <TemplateRuleValidator
            nodes={allNodes}
            edges={allEdges}
            template={template}
            onValidationComplete={(results) => {
              console.log('Validation results:', results);
            }}
          />
        )}

        {/* AI Assistant */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm flex items-center space-x-2">
              <Bot className="h-4 w-4" />
              <span>AI Assistant</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="flex items-start space-x-2">
                <Bot className="h-4 w-4 text-blue-500 mt-1 flex-shrink-0" />
                <div>
                  <p className="text-sm text-blue-800 mb-2">
                    I notice this is a {selectedNode.data.type} node.
                  </p>
                  <p className="text-xs text-blue-700">
                    {selectedNode.data.type === 'usecase' &&
                      'Consider adding proper error handling and validation.'}
                    {selectedNode.data.type === 'adapter' &&
                      'Ensure this adapter implements the proper interface.'}
                    {selectedNode.data.type === 'entity' &&
                      'Make sure this entity follows domain modeling principles.'}
                    {selectedNode.data.type === 'controller' &&
                      'Consider keeping this controller thin and delegating to use cases.'}
                    {selectedNode.data.type === 'repository' &&
                      'Ensure this repository abstracts data access properly.'}
                  </p>
                </div>
              </div>
            </div>

            <div className="flex space-x-2">
              <Input
                value={aiInput}
                onChange={(e) => setAiInput(e.target.value)}
                placeholder="Ask about this node..."
                onKeyDown={(e) => e.key === 'Enter' && handleAiQuestion()}
              />
              <Button size="sm" onClick={handleAiQuestion}>
                <Bot className="h-4 w-4" />
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Actions */}
      <div className="p-4 border-t border-gray-200 space-y-3">
        <Button
          onClick={handleSave}
          className="w-full"
          disabled={updateNodeMutation.isPending}
        >
          <Save className="h-4 w-4 mr-2" />
          {updateNodeMutation.isPending ? 'Saving...' : 'Save Changes'}
        </Button>

        <div className="flex space-x-2">
          <Button
            variant="secondary"
            onClick={handleDuplicate}
            className="flex-1"
          >
            <Copy className="h-4 w-4 mr-2" />
            Duplicate
          </Button>
          <Button
            variant="destructive"
            onClick={handleDelete}
            disabled={deleteNodeMutation.isPending}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
