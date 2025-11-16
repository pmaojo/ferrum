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
import { useUpdateEdge } from '@/hooks/use-graph';
import { useToast } from '@/hooks/use-toast';
import { Save, X, Link, ArrowRight } from 'lucide-react';
import type { Edge } from 'reactflow';
import type { GraphNodeData, EdgeParameter, MethodCall } from '@/types/graph';

interface NodeConnectionEditorProps {
  isOpen: boolean;
  onClose: () => void;
  sourceNode: { id: string; name: string; type: string } | null;
  targetNode: { id: string; name: string; type: string } | null;
  edge?: Edge | null;
}

const connectionTypes = [
  { value: 'uses', label: 'Uses', description: 'Source uses target' },
  {
    value: 'depends_on',
    label: 'Depends On',
    description: 'Source depends on target',
  },
  { value: 'manages', label: 'Manages', description: 'Source manages target' },
  {
    value: 'orchestrates',
    label: 'Orchestrates',
    description: 'Source orchestrates target',
  },
  {
    value: 'transforms',
    label: 'Transforms',
    description: 'Source transforms target',
  },
  {
    value: 'contains',
    label: 'Contains',
    description: 'Source contains target',
  },
  {
    value: 'implements',
    label: 'Implements',
    description: 'Source implements target',
  },
  {
    value: 'calls',
    label: 'Calls',
    description: 'Source calls methods on target',
  },
  { value: 'related', label: 'Related', description: 'General relationship' },
];

export function NodeConnectionEditor({
  isOpen,
  onClose,
  sourceNode,
  targetNode,
  edge,
}: NodeConnectionEditorProps) {
  const updateEdgeMutation = useUpdateEdge();
  const { toast } = useToast();

  const [formData, setFormData] = useState<{
    type: string;
    label: string;
    description: string;
    bidirectional: boolean;
    parameters: EdgeParameter[];
    methodCalls: MethodCall[];
  }>({
    type: 'uses',
    label: '',
    description: '',
    bidirectional: false,
    parameters: [],
    methodCalls: [],
  });

  useEffect(() => {
    if (edge) {
      setFormData({
        type: edge.data?.type || edge.type || 'uses',
        label: (edge.label as string) || '',
        description: edge.data?.description || '',
        bidirectional: edge.data?.bidirectional || false,
        parameters: edge.data?.parameters || [],
        methodCalls: edge.data?.methodCalls || [],
      });
    } else if (sourceNode && targetNode) {
      // Auto-suggest connection type based on node types
      const suggestedType = getSuggestedConnectionType(
        sourceNode.type,
        targetNode.type
      );
      setFormData({
        type: suggestedType,
        label: `${sourceNode.name} → ${targetNode.name}`,
        description: getConnectionDescription(
          sourceNode,
          targetNode,
          suggestedType
        ),
        bidirectional: false,
        parameters: [],
        methodCalls: [],
      });
    }
  }, [edge, sourceNode, targetNode]);

  const getSuggestedConnectionType = (
    sourceType: string,
    targetType: string
  ): string => {
    // Smart suggestions based on common patterns
    if (sourceType === 'controller' && targetType === 'service') return 'uses';
    if (sourceType === 'service' && targetType === 'repository') return 'uses';
    if (sourceType === 'repository' && targetType === 'entity')
      return 'manages';
    if (sourceType === 'controller' && targetType === 'dto') return 'uses';
    if (sourceType === 'service' && targetType === 'entity')
      return 'transforms';
    if (sourceType === 'usecase' && targetType === 'repository')
      return 'depends_on';
    return 'uses';
  };

  const getConnectionDescription = (
    source: any,
    target: any,
    type: string
  ): string => {
    const descriptions: Record<string, string> = {
      uses: `${source.name} uses ${target.name} for ${target.type} operations`,
      depends_on: `${source.name} depends on ${target.name} to function properly`,
      manages: `${source.name} manages the lifecycle of ${target.name}`,
      orchestrates: `${source.name} orchestrates operations through ${target.name}`,
      transforms: `${source.name} transforms data using ${target.name}`,
      contains: `${source.name} contains ${target.name} as a component`,
      implements: `${source.name} implements the interface defined by ${target.name}`,
      calls: `${source.name} calls methods on ${target.name}`,
      related: `${source.name} is related to ${target.name}`,
    };
    return (
      descriptions[type] || `${source.name} is connected to ${target.name}`
    );
  };

  const handleSave = () => {
    if (!edge) return;

    const updatedData = {
      type: formData.type,
      label: formData.label,
      description: formData.description,
      bidirectional: formData.bidirectional,
      parameters: formData.parameters || [],
      methodCalls: formData.methodCalls || [],
    };

    updateEdgeMutation.mutate(
      { id: edge.id, data: updatedData },
      {
        onSuccess: () => {
          toast({
            title: 'CONNECTION_UPDATED',
            description: 'Connection properties saved successfully',
          });
          onClose();
        },
        onError: () => {
          toast({
            title: 'ERROR',
            description: 'Failed to update connection',
            variant: 'destructive',
          });
        },
      }
    );
  };

  if (!sourceNode || !targetNode) return null;

  const selectedConnectionType = connectionTypes.find(
    (ct) => ct.value === formData.type
  );

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="bg-black border-[#00FF41] text-[#00FF41] max-w-lg font-mono">
        <DialogHeader>
          <DialogTitle className="font-mono text-[#00FF41] text-lg flex items-center space-x-2">
            <Link className="h-5 w-5" />
            <span>CONNECTION_EDITOR</span>
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-6">
          {/* Connection Visual */}
          <div className="p-4 border border-[#00FF41]/30 rounded bg-black/50">
            <div className="flex items-center justify-between">
              <div className="text-center">
                <Badge
                  variant="outline"
                  className="border-[#00FFFF] text-[#00FFFF] mb-2"
                >
                  {sourceNode.type.toUpperCase()}
                </Badge>
                <div className="text-[#00FF41] text-sm font-bold">
                  {sourceNode.name}
                </div>
              </div>

              <div className="flex items-center space-x-2">
                <ArrowRight className="h-6 w-6 text-[#FF00FF]" />
                {formData.bidirectional && (
                  <ArrowRight className="h-6 w-6 text-[#FF00FF] rotate-180" />
                )}
              </div>

              <div className="text-center">
                <Badge
                  variant="outline"
                  className="border-[#FFFF00] text-[#FFFF00] mb-2"
                >
                  {targetNode.type.toUpperCase()}
                </Badge>
                <div className="text-[#00FF41] text-sm font-bold">
                  {targetNode.name}
                </div>
              </div>
            </div>
          </div>

          {/* Connection Type */}
          <div>
            <Label className="text-[#00FF41] font-mono text-sm mb-2 block">
              CONNECTION_TYPE:
            </Label>
            <Select
              value={formData.type}
              onValueChange={(value) => {
                setFormData((prev) => ({
                  ...prev,
                  type: value,
                  description: getConnectionDescription(
                    sourceNode,
                    targetNode,
                    value
                  ),
                }));
              }}
            >
              <SelectTrigger className="bg-black border-[#00FF41] text-[#00FF41] font-mono">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-black border-[#00FF41] text-[#00FF41]">
                {connectionTypes.map((type) => (
                  <SelectItem
                    key={type.value}
                    value={type.value}
                    className="font-mono hover:bg-[#00FF41]/10"
                  >
                    <div>
                      <div className="font-bold">{type.label}</div>
                      <div className="text-xs text-[#00FF41]/70">
                        {type.description}
                      </div>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {selectedConnectionType && (
              <div className="text-[#00FF41]/70 font-mono text-xs mt-1">
                {selectedConnectionType.description}
              </div>
            )}
          </div>

          {/* Connection Label */}
          <div>
            <Label className="text-[#00FF41] font-mono text-sm mb-2 block">
              LABEL:
            </Label>
            <Input
              value={formData.label}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, label: e.target.value }))
              }
              placeholder="Connection label..."
              className="bg-black border-[#00FF41] text-[#00FF41] font-mono placeholder:text-[#00FF41]/50"
            />
          </div>

          {/* Description */}
          <div>
            <Label className="text-[#00FF41] font-mono text-sm mb-2 block">
              DESCRIPTION:
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
              className="bg-black border-[#00FF41] text-[#00FF41] font-mono placeholder:text-[#00FF41]/50"
            />
          </div>

          {/* Actions */}
          <div className="flex space-x-2 pt-4">
            <Button
              onClick={onClose}
              className="flex-1 bg-transparent border border-[#00FF41] text-[#00FF41] hover:bg-[#00FF41]/10 font-mono"
            >
              <X className="h-4 w-4 mr-2" />
              CANCEL
            </Button>
            <Button
              onClick={handleSave}
              disabled={!edge || updateEdgeMutation.isPending}
              className="flex-1 bg-[#00FF41] text-black hover:bg-[#00FF41]/80 font-mono"
            >
              <Save className="h-4 w-4 mr-2" />
              {updateEdgeMutation.isPending ? 'SAVING...' : 'SAVE'}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
