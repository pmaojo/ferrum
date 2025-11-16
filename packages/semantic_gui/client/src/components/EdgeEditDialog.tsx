import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { useUpdateEdge, useDeleteEdge } from '@/hooks/use-graph';
import { useToast } from '@/hooks/use-toast';
import { Save, Trash2, AlertTriangle, X } from 'lucide-react';
import type { Edge } from 'reactflow';
import type {
  ValidationRule,
  EdgeParameter,
  MethodCall,
} from '@/types/graph';

interface EdgeEditDialogProps {
  edge: Edge | null;
  isOpen: boolean;
  onClose: () => void;
  templateRules?: ValidationRule[];
}

export function EdgeEditDialog({
  edge,
  isOpen,
  onClose,
  templateRules = [],
}: EdgeEditDialogProps) {
  const updateEdgeMutation = useUpdateEdge();
  const deleteEdgeMutation = useDeleteEdge();
  const { toast } = useToast();

  const [formData, setFormData] = useState<{
    type: string;
    label: string;
    description: string;
    parameters: EdgeParameter[];
    methodCalls: MethodCall[];
  }>({
    type: '',
    label: '',
    description: '',
    parameters: [],
    methodCalls: [],
  });

  const [newParameter, setNewParameter] = useState<EdgeParameter>({
    name: '',
    type: '',
    direction: 'input',
    required: false,
  });

  const [newMethodCall, setNewMethodCall] = useState<MethodCall>({
    methodName: '',
    parameters: [],
    returnType: '',
  });

  const [ruleViolations, setRuleViolations] = useState<string[]>([]);

  useEffect(() => {
    if (edge) {
      setFormData({
        type: edge.data?.type || edge.type || '',
        label: (edge.label as string) || '',
        description: edge.data?.description || '',
        parameters: edge.data?.parameters || [],
        methodCalls: edge.data?.methodCalls || [],
      });
      validateAgainstRules();
    }
  }, [edge]);

  const validateAgainstRules = () => {
    if (!edge || !templateRules.length) return;

    const violations: string[] = [];

    // Check template-specific rules
    templateRules.forEach((rule) => {
      if (rule.type === 'prohibited') {
        // Implementation would check if this edge violates template rules
        // This is a simplified example
      }
    });

    setRuleViolations(violations);
  };

  const connectionTypes = [
    'uses',
    'depends_on',
    'manages',
    'orchestrates',
    'transforms',
    'contains',
    'implements',
    'depends',
    'calls',
    'related',
  ];

  const handleSave = () => {
    if (!edge) return;

    const updatedData = {
      ...edge.data,
      type: formData.type,
      label: formData.label,
      description: formData.description,
      parameters: formData.parameters,
      methodCalls: formData.methodCalls,
    };

    updateEdgeMutation.mutate(
      { id: edge.id, data: updatedData },
      {
        onSuccess: () => {
          toast({
            title: 'Connection updated',
            description: 'Connection properties have been saved.',
          });
          onClose();
        },
        onError: () => {
          toast({
            title: 'Error',
            description: 'Failed to update connection.',
            variant: 'destructive',
          });
        },
      }
    );
  };

  const handleDelete = () => {
    if (!edge) return;

    deleteEdgeMutation.mutate(edge.id, {
      onSuccess: () => {
        toast({
          title: 'Connection deleted',
          description: 'Connection has been removed.',
        });
        onClose();
      },
      onError: () => {
        toast({
          title: 'Error',
          description: 'Failed to delete connection.',
          variant: 'destructive',
        });
      },
    });
  };

  const addParameter = () => {
    if (!newParameter.name || !newParameter.type) return;

    setFormData((prev) => ({
      ...prev,
      parameters: [...prev.parameters, newParameter],
    }));

    setNewParameter({
      name: '',
      type: '',
      direction: 'input',
      required: false,
    });
  };

  const removeParameter = (index: number) => {
    setFormData((prev) => ({
      ...prev,
      parameters: prev.parameters.filter((_, i) => i !== index),
    }));
  };

  const addMethodCall = () => {
    if (!newMethodCall.methodName) return;

    setFormData((prev) => ({
      ...prev,
      methodCalls: [...prev.methodCalls, newMethodCall],
    }));

    setNewMethodCall({
      methodName: '',
      parameters: [],
      returnType: '',
    });
  };

  const removeMethodCall = (index: number) => {
    setFormData((prev) => ({
      ...prev,
      methodCalls: prev.methodCalls.filter((_, i) => i !== index),
    }));
  };

  if (!edge) return null;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto bg-card border-2 border-primary">
        <DialogHeader>
          <DialogTitle className="text-primary terminal-font font-black">
            EDIT_CONNECTION
          </DialogTitle>
          <div className="text-sm text-primary/70 terminal-font">
            {edge.source} → {edge.target}
          </div>
        </DialogHeader>

        <div className="space-y-6">
          {/* Rule Violations Warning */}
          {ruleViolations.length > 0 && (
            <div className="border-2 border-red-500 bg-red-900/20 p-3 rounded">
              <div className="flex items-center space-x-2 text-red-400 mb-2">
                <AlertTriangle className="h-4 w-4" />
                <span className="font-black terminal-font">
                  RULE_VIOLATIONS
                </span>
              </div>
              {ruleViolations.map((violation, idx) => (
                <div key={idx} className="text-xs text-red-300 terminal-font">
                  • {violation}
                </div>
              ))}
            </div>
          )}

          {/* Connection Type */}
          <div>
            <Label className="text-primary terminal-font font-black">
              CONNECTION_TYPE
            </Label>
            <Select
              value={formData.type}
              onValueChange={(value) =>
                setFormData((prev) => ({ ...prev, type: value }))
              }
            >
              <SelectTrigger className="bg-input border-2 border-primary text-primary terminal-font">
                <SelectValue placeholder="SELECT_TYPE..." />
              </SelectTrigger>
              <SelectContent className="bg-card border-2 border-primary">
                {connectionTypes.map((type) => (
                  <SelectItem
                    key={type}
                    value={type}
                    className="text-primary terminal-font"
                  >
                    {type.toUpperCase()}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Label */}
          <div>
            <Label className="text-primary terminal-font font-black">
              LABEL
            </Label>
            <Input
              value={formData.label}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, label: e.target.value }))
              }
              placeholder="Connection label..."
              className="bg-input border-2 border-primary text-primary terminal-font"
            />
          </div>

          {/* Description */}
          <div>
            <Label className="text-primary terminal-font font-black">
              DESCRIPTION
            </Label>
            <Textarea
              value={formData.description}
              onChange={(e) =>
                setFormData((prev) => ({
                  ...prev,
                  description: e.target.value,
                }))
              }
              placeholder="Describe this connection..."
              rows={3}
              className="bg-input border-2 border-primary text-primary terminal-font"
            />
          </div>

          {/* Parameters Section */}
          <div>
            <Label className="text-primary terminal-font font-black">
              PARAMETERS
            </Label>

            {/* Existing Parameters */}
            <div className="space-y-2 mb-3">
              {formData.parameters.map((param, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between bg-primary/10 p-2 rounded border border-primary/30"
                >
                  <div className="flex items-center space-x-2">
                    <span className="text-primary terminal-font text-sm">
                      {param.name}
                    </span>
                    <Badge
                      variant="outline"
                      className="text-xs border-secondary text-secondary"
                    >
                      {param.type}
                    </Badge>
                    <Badge
                      variant="outline"
                      className="text-xs border-primary text-primary"
                    >
                      {param.direction}
                    </Badge>
                    {param.required && (
                      <Badge variant="destructive" className="text-xs">
                        REQUIRED
                      </Badge>
                    )}
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => removeParameter(idx)}
                    className="border-red-500 text-red-500 hover:bg-red-500/20"
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </div>
              ))}
            </div>

            {/* Add New Parameter */}
            <div className="grid grid-cols-4 gap-2">
              <Input
                placeholder="Name"
                value={newParameter.name}
                onChange={(e) =>
                  setNewParameter((prev) => ({ ...prev, name: e.target.value }))
                }
                className="bg-input border border-primary/50 text-primary terminal-font text-xs"
              />
              <Input
                placeholder="Type"
                value={newParameter.type}
                onChange={(e) =>
                  setNewParameter((prev) => ({ ...prev, type: e.target.value }))
                }
                className="bg-input border border-primary/50 text-primary terminal-font text-xs"
              />
              <Select
                value={newParameter.direction}
                onValueChange={(value: EdgeParameter['direction']) =>
                  setNewParameter((prev) => ({ ...prev, direction: value }))
                }
              >
                <SelectTrigger className="bg-input border border-primary/50 text-primary terminal-font text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="input">INPUT</SelectItem>
                  <SelectItem value="output">OUTPUT</SelectItem>
                  <SelectItem value="bidirectional">BOTH</SelectItem>
                </SelectContent>
              </Select>
              <Button
                onClick={addParameter}
                size="sm"
                className="terminal-font text-xs"
              >
                ADD
              </Button>
            </div>
          </div>

          {/* Method Calls Section */}
          <div>
            <Label className="text-primary terminal-font font-black">
              METHOD_CALLS
            </Label>

            {/* Existing Method Calls */}
            <div className="space-y-2 mb-3">
              {formData.methodCalls.map((method, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between bg-primary/10 p-2 rounded border border-primary/30"
                >
                  <div className="flex-1">
                    <div className="text-primary terminal-font text-sm">
                      {method.methodName}()
                    </div>
                    {method.parameters?.length > 0 && (
                      <div className="text-primary/70 terminal-font text-xs">
                        params: {method.parameters.join(', ')}
                      </div>
                    )}
                    {method.returnType && (
                      <div className="text-secondary terminal-font text-xs">
                        → {method.returnType}
                      </div>
                    )}
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => removeMethodCall(idx)}
                    className="border-red-500 text-red-500 hover:bg-red-500/20"
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </div>
              ))}
            </div>

            {/* Add New Method Call */}
            <div className="grid grid-cols-4 gap-2">
              <Input
                placeholder="Method name"
                value={newMethodCall.methodName}
                onChange={(e) =>
                  setNewMethodCall((prev) => ({
                    ...prev,
                    methodName: e.target.value,
                  }))
                }
                className="bg-input border border-primary/50 text-primary terminal-font text-xs"
              />
              <Input
                placeholder="Params (comma-separated)"
                value={newMethodCall.parameters?.join(', ')}
                onChange={(e) =>
                  setNewMethodCall((prev) => ({
                    ...prev,
                    parameters: e.target.value
                      .split(',')
                      .map((p) => p.trim())
                      .filter(Boolean),
                  }))
                }
                className="bg-input border border-primary/50 text-primary terminal-font text-xs"
              />
              <Input
                placeholder="Return type"
                value={newMethodCall.returnType}
                onChange={(e) =>
                  setNewMethodCall((prev) => ({
                    ...prev,
                    returnType: e.target.value,
                  }))
                }
                className="bg-input border border-primary/50 text-primary terminal-font text-xs"
              />
              <Button
                onClick={addMethodCall}
                size="sm"
                className="terminal-font text-xs"
              >
                ADD
              </Button>
            </div>
          </div>

          {/* Actions */}
          <div className="flex justify-between pt-4 border-t border-primary/30">
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteEdgeMutation.isPending}
              className="terminal-font"
            >
              <Trash2 className="h-4 w-4 mr-2" />
              DELETE
            </Button>

            <div className="flex space-x-2">
              <Button
                variant="outline"
                onClick={onClose}
                className="terminal-font"
              >
                CANCEL
              </Button>
              <Button
                onClick={handleSave}
                disabled={updateEdgeMutation.isPending}
                className="terminal-font"
              >
                <Save className="h-4 w-4 mr-2" />
                {updateEdgeMutation.isPending ? 'SAVING...' : 'SAVE'}
              </Button>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
