import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { GraphNodeData } from '@/types/graph';

const nodeTypeStyles = {
  // @kthulu:extend - Semantic Kthulu Architecture Node Types
  module: {
    gradient: 'bg-purple-500/20',
    border: 'border-purple-500',
    bg: 'bg-card',
    icon: '🏗️',
    special: true,
    semantic: true,
    description: 'Bounded Context Module',
  },
  usecase: {
    gradient: 'bg-blue-500/30',
    border: 'border-blue-500',
    bg: 'bg-card',
    icon: '⚡',
    special: true,
    semantic: true,
    description: 'Domain Use Case',
  },
  adapter: {
    gradient: 'bg-orange-500/20',
    border: 'border-orange-500',
    bg: 'bg-card',
    icon: '🔌',
    semantic: true,
    description: 'Infrastructure Adapter',
  },
  port: {
    gradient: 'bg-green-500/20',
    border: 'border-green-500',
    bg: 'bg-card',
    icon: '🚪',
    semantic: true,
    description: 'Domain Port',
  },
  domainentity: {
    gradient: 'bg-cyan-500/20',
    border: 'border-cyan-500',
    bg: 'bg-card',
    icon: '💎',
    semantic: true,
    description: 'Domain Entity',
  },
  domainevent: {
    gradient: 'bg-yellow-500/20',
    border: 'border-yellow-500',
    bg: 'bg-card',
    icon: '⚡',
    semantic: true,
    description: 'Domain Event',
  },
  aggregateroot: {
    gradient: 'bg-indigo-500/20',
    border: 'border-indigo-500',
    bg: 'bg-card',
    icon: '👑',
    semantic: true,
    description: 'Aggregate Root',
  },
  // Legacy types for backwards compatibility
  domain: {
    gradient: 'bg-primary/15',
    border: 'border-primary',
    bg: 'bg-card',
    icon: '[DOMAIN]',
  },
  // Legacy/supporting types for backwards compatibility
  entity: {
    gradient: 'bg-primary/15',
    border: 'border-primary',
    bg: 'bg-card',
    icon: '[ENTTY]',
  },
  controller: {
    gradient: 'bg-primary/25',
    border: 'border-primary',
    bg: 'bg-card',
    icon: '[CTRL]',
  },
  repository: {
    gradient: 'bg-secondary/15',
    border: 'border-secondary',
    bg: 'bg-card',
    icon: '[REPO]',
  },
  service: {
    gradient: 'bg-primary/30',
    border: 'border-primary',
    bg: 'bg-card',
    icon: '[SERV]',
  },
  dto: {
    gradient: 'bg-primary/10',
    border: 'border-primary',
    bg: 'bg-card',
    icon: '[DTO]',
  },
  guard: {
    gradient: 'bg-secondary/25',
    border: 'border-secondary',
    bg: 'bg-card',
    icon: '[GUARD]',
  },
  middleware: {
    gradient: 'bg-primary/35',
    border: 'border-primary',
    bg: 'bg-card',
    icon: '[MWARE]',
  },
  // @kthulu:extend - Semantic Violation Types
  violation: {
    gradient: 'bg-red-500/20',
    border: 'border-red-500',
    icon: '⚠️',
  },
  dip_violation: {
    gradient: 'bg-red-600/30',
    border: 'border-red-600',
    bg: 'bg-red-50',
    icon: '🚫',
    description: 'DIP Violation: Domain → Infrastructure',
  },
  ddd_violation: {
    gradient: 'bg-orange-600/30',
    border: 'border-orange-600',
    bg: 'bg-orange-50',
    icon: '⛔',
    description: 'DDD Violation: Bounded Context Breach',
  },
  solid_violation: {
    gradient: 'bg-yellow-600/30',
    border: 'border-yellow-600',
    bg: 'bg-yellow-50',
    icon: '⚡',
    description: 'SOLID Violation: Design Principle',
  },
};

export const GraphNode = memo(
  ({ data, selected }: NodeProps<GraphNodeData>) => {
    const style =
      nodeTypeStyles[data.type as keyof typeof nodeTypeStyles] ||
      nodeTypeStyles.usecase;

    // @kthulu:extend - Enhanced violation detection with semantic types
    const getViolationStyle = () => {
      if (!data.violation) return {};

      // Determine violation type from message
      const message = data.violationMessage?.toLowerCase() || '';
      if (message.includes('dip') || message.includes('dependency inversion')) {
        return nodeTypeStyles.dip_violation;
      }
      if (
        message.includes('ddd') ||
        message.includes('bounded context') ||
        message.includes('domain')
      ) {
        return nodeTypeStyles.ddd_violation;
      }
      if (
        message.includes('solid') ||
        message.includes('single responsibility') ||
        message.includes('open closed')
      ) {
        return nodeTypeStyles.solid_violation;
      }
      return nodeTypeStyles.violation;
    };

    const violationStyle = getViolationStyle();
    const isUseCase = data.type === 'usecase';
    const isModule = data.type === 'module';
    const isSemantic = style.semantic || false;
    const hasViolation = data.violation;

    return (
      <Card
        title={data.violationMessage}
        className={cn(
          'transition-all duration-100 hover:shadow-lg border-2 terminal-font hacker-glow hacker-border',
          isModule ? 'w-64' : isUseCase ? 'w-56 border-3' : 'w-48',
          style.border,
          violationStyle.border,
          isUseCase &&
            'shadow-accent/20 shadow-lg border-accent animate-pulse-subtle',
          selected &&
            'ring-2 ring-primary ring-offset-2 ring-offset-background hacker-text-glow'
        )}
      >
        {/* @kthulu:extend - Enhanced Semantic Header */}
        <div
          className={cn(
            'px-3 py-2 terminal-font',
            hasViolation
              ? 'text-red-600'
              : isUseCase
                ? 'text-accent'
                : 'text-primary',
            hasViolation ? violationStyle.gradient : style.gradient,
            isUseCase && !hasViolation && 'bg-accent/40 border-b border-accent',
            hasViolation && 'border-b-2 animate-pulse'
          )}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span
                className={cn(
                  'text-lg font-black',
                  isUseCase && !hasViolation && 'animate-bounce-subtle',
                  hasViolation && 'animate-pulse text-red-600'
                )}
              >
                {hasViolation ? violationStyle.icon : style.icon}
              </span>
              <span className="text-xs font-black uppercase tracking-wide">
                {data.type.toUpperCase()}
              </span>
              {isModule && (
                <span className="ml-1 text-xs font-black">
                  {data.collapsed ? '+' : '-'}
                </span>
              )}
              {isUseCase && !hasViolation && (
                <span className="text-xs font-black text-accent animate-pulse">
                  CORE
                </span>
              )}
              {isSemantic && (
                <Badge
                  variant="outline"
                  className="text-xs px-1 py-0 border-current"
                >
                  OWL
                </Badge>
              )}
              {hasViolation && (
                <Badge
                  variant="destructive"
                  className="text-xs px-1 py-0 animate-pulse"
                >
                  VIOLATION
                </Badge>
              )}
            </div>
            <div className="flex space-x-1">
              <div
                className={cn(
                  'w-2 h-2 rounded-full',
                  hasViolation
                    ? 'bg-red-500 animate-pulse'
                    : isUseCase
                      ? 'bg-accent hacker-text-glow'
                      : 'bg-primary hacker-text-glow'
                )}
              ></div>
              <div
                className={cn(
                  'w-2 h-2 rounded-full',
                  hasViolation ? 'bg-red-300' : 'bg-secondary'
                )}
              ></div>
            </div>
          </div>
        </div>

        {/* @kthulu:extend - Enhanced Semantic Content */}
        <CardContent
          className={cn('p-3', hasViolation ? violationStyle.bg : style.bg)}
        >
          <h3
            className={cn(
              'font-black text-sm mb-1 line-clamp-1 terminal-font hacker-text-glow',
              hasViolation ? 'text-red-600' : 'text-primary'
            )}
          >
            {data.name.toUpperCase()}
          </h3>

          {/* Semantic Description */}
          {isSemantic && style.description && (
            <p className="text-xs text-muted-foreground mb-1 terminal-font italic">
              {style.description}
            </p>
          )}

          {data.filePath && (
            <p className="text-xs text-primary/70 mb-2 terminal-font line-clamp-1">
              📁 {data.filePath}
            </p>
          )}

          {data.description && (
            <p className="text-xs text-primary/80 mb-2 line-clamp-2 terminal-font">
              {'>'} {data.description}
            </p>
          )}

          {/* Violation Details */}
          {hasViolation && data.violationMessage && (
            <div className="mb-2 p-2 bg-red-50 border border-red-200 rounded">
              <p className="text-xs text-red-700 terminal-font font-bold">
                🚨 VIOLATION DETECTED
              </p>
              <p className="text-xs text-red-600 terminal-font line-clamp-2">
                {data.violationMessage}
              </p>
            </div>
          )}

          {/* Semantic Metadata */}
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-1">
              {data.metadata?.complexity && (
                <Badge
                  variant="outline"
                  className={cn(
                    'text-xs px-1 py-0 terminal-font font-black',
                    hasViolation
                      ? 'border-red-500 text-red-600'
                      : 'border-primary text-primary'
                  )}
                >
                  {data.metadata.complexity.toUpperCase()}
                </Badge>
              )}
              {data.metadata?.moduleNamespace && (
                <Badge
                  variant="secondary"
                  className="text-xs px-1 py-0 terminal-font"
                >
                  {data.metadata.moduleNamespace}
                </Badge>
              )}
              {isSemantic && (
                <Badge
                  variant="outline"
                  className="text-xs px-1 py-0 border-green-500 text-green-600 terminal-font"
                >
                  OWL
                </Badge>
              )}
            </div>

            <div className="text-xs text-primary/60 terminal-font">
              {data.metadata?.linesOfCode && `${data.metadata.linesOfCode}L`}
              {data.metadata?.dependencies &&
                ` • ${data.metadata.dependencies} deps`}
            </div>
          </div>

          {/* Semantic Relationships Preview */}
          {isSemantic && data.metadata?.relationships && (
            <div className="mt-2 pt-2 border-t border-muted">
              <p className="text-xs text-muted-foreground terminal-font">
                🔗 {data.metadata.relationships} semantic relations
              </p>
            </div>
          )}
        </CardContent>

        {/* BRUTAL CONNECTION HANDLES */}
        <Handle
          type="target"
          position={Position.Left}
          className="w-3 h-3 bg-primary border-2 border-background hover:bg-primary/80 hacker-glow"
        />
        <Handle
          type="source"
          position={Position.Right}
          className="w-3 h-3 bg-secondary border-2 border-background hover:bg-secondary/80 hacker-glow"
        />
      </Card>
    );
  }
);

GraphNode.displayName = 'GraphNode';
