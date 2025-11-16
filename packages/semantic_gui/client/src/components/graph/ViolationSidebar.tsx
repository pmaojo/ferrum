import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';

interface Violation {
  id: string;
  type: 'DIP' | 'DDD' | 'SOLID';
  severity: 'error' | 'warning' | 'info';
  component: string;
  message: string;
  suggestion?: string;
  affectedNodes: string[];
  ruleId: string;
}

interface ViolationSidebarProps {
  violations: Violation[];
  onViolationClick: (violation: Violation) => void;
  onFixSuggestion: (violation: Violation) => void;
  className?: string;
}

const violationTypeStyles = {
  DIP: {
    color: 'text-red-600',
    bg: 'bg-red-50',
    border: 'border-red-200',
    icon: '🚫',
    description: 'Dependency Inversion Principle',
  },
  DDD: {
    color: 'text-orange-600',
    bg: 'bg-orange-50',
    border: 'border-orange-200',
    icon: '⛔',
    description: 'Domain-Driven Design',
  },
  SOLID: {
    color: 'text-yellow-600',
    bg: 'bg-yellow-50',
    border: 'border-yellow-200',
    icon: '⚡',
    description: 'SOLID Principles',
  },
};

const severityStyles = {
  error: {
    color: 'text-red-600',
    bg: 'bg-red-100',
    label: 'ERROR',
  },
  warning: {
    color: 'text-yellow-600',
    bg: 'bg-yellow-100',
    label: 'WARNING',
  },
  info: {
    color: 'text-blue-600',
    bg: 'bg-blue-100',
    label: 'INFO',
  },
};

/**
 * @kthulu:extend - Violation sidebar for semantic architecture analysis
 * Shows detailed violation information with fix suggestions
 */
export function ViolationSidebar({
  violations,
  onViolationClick,
  onFixSuggestion,
  className,
}: ViolationSidebarProps) {
  const violationsByType = violations.reduce(
    (acc, violation) => {
      if (!acc[violation.type]) {
        acc[violation.type] = [];
      }
      acc[violation.type].push(violation);
      return acc;
    },
    {} as Record<string, Violation[]>
  );

  const totalViolations = violations.length;
  const errorCount = violations.filter((v) => v.severity === 'error').length;
  const warningCount = violations.filter(
    (v) => v.severity === 'warning'
  ).length;

  if (totalViolations === 0) {
    return (
      <Card className={cn('w-80', className)}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            ✅ Architecture Validation
            <Badge
              variant="outline"
              className="text-green-600 border-green-600"
            >
              Clean
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <div className="text-4xl mb-2">🎉</div>
            <p className="text-green-600 font-medium">
              No violations detected!
            </p>
            <p className="text-sm text-muted-foreground mt-1">
              Your architecture follows all semantic rules.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={cn('w-80', className)}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          🚨 Architecture Violations
          <Badge variant="destructive">{totalViolations}</Badge>
        </CardTitle>
        <div className="flex gap-2 text-sm">
          {errorCount > 0 && (
            <Badge variant="destructive" className="text-xs">
              {errorCount} Errors
            </Badge>
          )}
          {warningCount > 0 && (
            <Badge variant="secondary" className="text-xs">
              {warningCount} Warnings
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <ScrollArea className="h-96">
          <div className="p-4 space-y-4">
            {Object.entries(violationsByType).map(([type, typeViolations]) => {
              const style =
                violationTypeStyles[type as keyof typeof violationTypeStyles];

              return (
                <div key={type}>
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-lg">{style.icon}</span>
                    <h3 className="font-semibold text-sm">
                      {style.description}
                    </h3>
                    <Badge
                      variant="outline"
                      className={cn('text-xs', style.color)}
                    >
                      {typeViolations.length}
                    </Badge>
                  </div>

                  <div className="space-y-2 ml-6">
                    {typeViolations.map((violation) => {
                      const severityStyle = severityStyles[violation.severity];

                      return (
                        <Card
                          key={violation.id}
                          className={cn(
                            'cursor-pointer transition-all hover:shadow-md',
                            style.bg,
                            style.border
                          )}
                          onClick={() => onViolationClick(violation)}
                        >
                          <CardContent className="p-3">
                            <div className="flex items-start justify-between mb-2">
                              <div className="flex items-center gap-2">
                                <Badge
                                  variant="outline"
                                  className={cn('text-xs', severityStyle.color)}
                                >
                                  {severityStyle.label}
                                </Badge>
                                <span className="text-xs text-muted-foreground">
                                  {violation.ruleId}
                                </span>
                              </div>
                            </div>

                            <p className="text-sm font-medium mb-1">
                              {violation.component}
                            </p>

                            <p className="text-xs text-muted-foreground mb-2 line-clamp-2">
                              {violation.message}
                            </p>

                            {violation.affectedNodes.length > 0 && (
                              <div className="flex flex-wrap gap-1 mb-2">
                                {violation.affectedNodes
                                  .slice(0, 3)
                                  .map((nodeId) => (
                                    <Badge
                                      key={nodeId}
                                      variant="secondary"
                                      className="text-xs"
                                    >
                                      {nodeId}
                                    </Badge>
                                  ))}
                                {violation.affectedNodes.length > 3 && (
                                  <Badge
                                    variant="secondary"
                                    className="text-xs"
                                  >
                                    +{violation.affectedNodes.length - 3} more
                                  </Badge>
                                )}
                              </div>
                            )}

                            {violation.suggestion && (
                              <div className="mt-2 pt-2 border-t border-current/20">
                                <p className="text-xs text-muted-foreground mb-2">
                                  💡 Suggested fix:
                                </p>
                                <p className="text-xs font-medium mb-2">
                                  {violation.suggestion}
                                </p>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  className="text-xs h-6"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    onFixSuggestion(violation);
                                  }}
                                >
                                  Apply Fix
                                </Button>
                              </div>
                            )}
                          </CardContent>
                        </Card>
                      );
                    })}
                  </div>

                  {Object.keys(violationsByType).indexOf(type) <
                    Object.keys(violationsByType).length - 1 && (
                    <Separator className="mt-4" />
                  )}
                </div>
              );
            })}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
