import React, { useState, useEffect, useRef } from 'react';
import {
  Code,
  Lightbulb,
  Package,
  Zap,
  ArrowRight,
  Check,
  X,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/hooks/use-toast';

interface SemanticCompletion {
  completion_text: string;
  completion_type: string;
  description: string;
  architectural_context: string;
  confidence: number;
  imports_needed: string[];
  pattern_type?: string;
  related_components?: string[];
  usage_examples?: string[];
}

interface CompletionContext {
  file_path: string;
  cursor_line: number;
  cursor_column: number;
  current_line: string;
  preceding_lines: string[];
  following_lines: string[];
  project_type: string;
  language: string;
  module_name?: string;
  component_type?: string;
}

interface SemanticCodeCompletionProps {
  filePath?: string;
  language?: string;
  onCompletionApply?: (completion: SemanticCompletion) => void;
  className?: string;
}

export const SemanticCodeCompletion: React.FC<SemanticCodeCompletionProps> = ({
  filePath = '',
  language = 'go',
  onCompletionApply,
  className = '',
}) => {
  const [code, setCode] = useState('');
  const [cursorPosition, setCursorPosition] = useState({ line: 0, column: 0 });
  const [completions, setCompletions] = useState<SemanticCompletion[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedCompletion, setSelectedCompletion] =
    useState<SemanticCompletion | null>(null);
  const [completionType, setCompletionType] = useState<string>('auto');
  const [showCompletions, setShowCompletions] = useState(false);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { toast } = useToast();

  // Auto-trigger completions when user types
  useEffect(() => {
    const timer = setTimeout(() => {
      if (code.trim() && showCompletions) {
        handleGetCompletions();
      }
    }, 500);

    return () => clearTimeout(timer);
  }, [code, cursorPosition]);

  const handleGetCompletions = async () => {
    if (!code.trim()) return;

    setIsLoading(true);
    setCompletions([]);

    try {
      const lines = code.split('\n');
      const currentLine = lines[cursorPosition.line] || '';
      const precedingLines = lines.slice(0, cursorPosition.line);
      const followingLines = lines.slice(cursorPosition.line + 1);

      // Extract partial input (word being typed)
      const beforeCursor = currentLine.substring(0, cursorPosition.column);
      const partialInput = beforeCursor.split(/\s+/).pop() || '';

      const context: CompletionContext = {
        file_path: filePath,
        cursor_line: cursorPosition.line,
        cursor_column: cursorPosition.column,
        current_line: currentLine,
        preceding_lines: precedingLines,
        following_lines: followingLines,
        project_type: 'kthulu',
        language: language,
        module_name: extractModuleName(filePath),
        component_type: detectComponentType(filePath, code),
      };

      const response = await fetch('/api/ai/semantic-completion', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          context,
          partial_input: partialInput,
          completion_type: completionType,
          max_suggestions: 10,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setCompletions(data.completions || []);

        if (data.completions && data.completions.length > 0) {
          setSelectedCompletion(data.completions[0]);
        }
      } else {
        throw new Error('Failed to get completions');
      }
    } catch (error) {
      console.error('Error getting completions:', error);
      toast({
        title: 'Completion failed',
        description: 'Failed to get semantic completions. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleApplyCompletion = (completion: SemanticCompletion) => {
    if (!textareaRef.current) return;

    const textarea = textareaRef.current;
    const lines = code.split('\n');
    const currentLine = lines[cursorPosition.line] || '';

    // Find the word being completed
    const beforeCursor = currentLine.substring(0, cursorPosition.column);
    const afterCursor = currentLine.substring(cursorPosition.column);
    const words = beforeCursor.split(/\s+/);
    const partialWord = words.pop() || '';
    const beforeWord = words.join(' ') + (words.length > 0 ? ' ' : '');

    // Replace the partial word with the completion
    const newLine = beforeWord + completion.completion_text + afterCursor;
    lines[cursorPosition.line] = newLine;

    const newCode = lines.join('\n');
    setCode(newCode);

    // Update cursor position
    const newCursorColumn =
      beforeWord.length + completion.completion_text.length;
    setCursorPosition({ line: cursorPosition.line, column: newCursorColumn });

    // Clear completions
    setCompletions([]);
    setSelectedCompletion(null);
    setShowCompletions(false);

    // Callback
    if (onCompletionApply) {
      onCompletionApply(completion);
    }

    toast({
      title: 'Completion applied',
      description: `Applied ${completion.completion_type} completion`,
    });
  };

  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    setCode(value);

    // Update cursor position
    const textarea = e.target;
    const cursorPos = textarea.selectionStart;
    const textBeforeCursor = value.substring(0, cursorPos);
    const lines = textBeforeCursor.split('\n');
    const line = lines.length - 1;
    const column = lines[lines.length - 1].length;

    setCursorPosition({ line, column });
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Trigger completions on Ctrl+Space
    if (e.ctrlKey && e.code === 'Space') {
      e.preventDefault();
      setShowCompletions(true);
      handleGetCompletions();
    }

    // Navigate completions with arrow keys
    if (completions.length > 0 && showCompletions) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        const currentIndex = completions.findIndex(
          (c) => c === selectedCompletion
        );
        const nextIndex = (currentIndex + 1) % completions.length;
        setSelectedCompletion(completions[nextIndex]);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        const currentIndex = completions.findIndex(
          (c) => c === selectedCompletion
        );
        const prevIndex =
          currentIndex <= 0 ? completions.length - 1 : currentIndex - 1;
        setSelectedCompletion(completions[prevIndex]);
      } else if (e.key === 'Enter' && selectedCompletion) {
        e.preventDefault();
        handleApplyCompletion(selectedCompletion);
      } else if (e.key === 'Escape') {
        setShowCompletions(false);
        setCompletions([]);
        setSelectedCompletion(null);
      }
    }
  };

  const getCompletionIcon = (type: string) => {
    const icons: Record<string, React.ReactNode> = {
      method: <Code className="h-4 w-4" />,
      type: <Package className="h-4 w-4" />,
      interface: <Package className="h-4 w-4" />,
      pattern: <Lightbulb className="h-4 w-4" />,
      import: <Package className="h-4 w-4" />,
      general: <Zap className="h-4 w-4" />,
    };
    return icons[type] || <Code className="h-4 w-4" />;
  };

  const getCompletionColor = (type: string) => {
    const colors: Record<string, string> = {
      method: 'bg-blue-100 text-blue-800 border-blue-200',
      type: 'bg-green-100 text-green-800 border-green-200',
      interface: 'bg-purple-100 text-purple-800 border-purple-200',
      pattern: 'bg-yellow-100 text-yellow-800 border-yellow-200',
      import: 'bg-gray-100 text-gray-800 border-gray-200',
      general: 'bg-orange-100 text-orange-800 border-orange-200',
    };
    return colors[type] || 'bg-gray-100 text-gray-800 border-gray-200';
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-600';
    if (confidence >= 0.6) return 'text-yellow-600';
    return 'text-red-600';
  };

  const extractModuleName = (filePath: string): string | undefined => {
    const parts = filePath.split('/');
    const internalIndex = parts.findIndex((part) => part === 'internal');
    if (internalIndex >= 0 && internalIndex + 1 < parts.length) {
      return parts[internalIndex + 1];
    }
    return undefined;
  };

  const detectComponentType = (
    filePath: string,
    code: string
  ): string | undefined => {
    const fileName = filePath.split('/').pop()?.toLowerCase() || '';

    if (fileName.includes('usecase')) return 'usecase';
    if (fileName.includes('adapter')) return 'adapter';
    if (fileName.includes('port') || fileName.includes('interface'))
      return 'port';
    if (fileName.includes('entity')) return 'entity';
    if (fileName.includes('service')) return 'service';

    return undefined;
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Code Editor */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg flex items-center gap-2">
              <Code className="h-5 w-5" />
              Semantic Code Completion
            </CardTitle>
            <div className="flex items-center gap-2">
              <select
                value={completionType}
                onChange={(e) => setCompletionType(e.target.value)}
                className="text-sm border rounded px-2 py-1"
              >
                <option value="auto">Auto</option>
                <option value="method">Methods</option>
                <option value="type">Types</option>
                <option value="import">Imports</option>
                <option value="pattern">Patterns</option>
              </select>
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  setShowCompletions(true);
                  handleGetCompletions();
                }}
                disabled={isLoading}
              >
                Get Completions
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="relative">
            <Textarea
              ref={textareaRef}
              value={code}
              onChange={handleTextareaChange}
              onKeyDown={handleKeyDown}
              placeholder={`Type your ${language} code here... Press Ctrl+Space for completions`}
              className="font-mono text-sm min-h-[300px] resize-none"
              spellCheck={false}
            />

            {/* Completion Popup */}
            {showCompletions && completions.length > 0 && (
              <Card className="absolute top-full left-0 right-0 z-10 mt-1 max-h-64 overflow-hidden shadow-lg">
                <ScrollArea className="max-h-64">
                  <div className="p-2">
                    {completions.map((completion, index) => (
                      <button
                        key={index}
                        onClick={() => handleApplyCompletion(completion)}
                        className={`w-full text-left p-3 rounded-lg border mb-2 transition-colors ${
                          selectedCompletion === completion
                            ? 'bg-blue-50 border-blue-200'
                            : 'hover:bg-gray-50'
                        }`}
                      >
                        <div className="flex items-start gap-3">
                          <div
                            className={`p-2 rounded-lg ${getCompletionColor(completion.completion_type)}`}
                          >
                            {getCompletionIcon(completion.completion_type)}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="font-mono text-sm font-medium truncate">
                                {completion.completion_text}
                              </span>
                              <Badge variant="outline" className="text-xs">
                                {completion.completion_type}
                              </Badge>
                              <span
                                className={`text-xs font-medium ${getConfidenceColor(completion.confidence)}`}
                              >
                                {(completion.confidence * 100).toFixed(0)}%
                              </span>
                            </div>
                            <p className="text-xs text-gray-600 mb-1">
                              {completion.description}
                            </p>
                            {completion.architectural_context && (
                              <p className="text-xs text-blue-600">
                                {completion.architectural_context}
                              </p>
                            )}
                            {completion.imports_needed &&
                              completion.imports_needed.length > 0 && (
                                <div className="flex items-center gap-1 mt-1">
                                  <Package className="h-3 w-3 text-gray-400" />
                                  <span className="text-xs text-gray-500">
                                    Imports:{' '}
                                    {completion.imports_needed.join(', ')}
                                  </span>
                                </div>
                              )}
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                </ScrollArea>
              </Card>
            )}
          </div>

          <div className="flex items-center justify-between text-sm text-gray-600">
            <span>
              Line {cursorPosition.line + 1}, Column {cursorPosition.column + 1}
            </span>
            <span>
              Press Ctrl+Space for completions • Use ↑↓ to navigate • Enter to
              apply • Esc to close
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Selected Completion Details */}
      {selectedCompletion && showCompletions && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Completion Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center gap-3">
              <div
                className={`p-2 rounded-lg ${getCompletionColor(selectedCompletion.completion_type)}`}
              >
                {getCompletionIcon(selectedCompletion.completion_type)}
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-mono font-medium">
                    {selectedCompletion.completion_text}
                  </span>
                  <Badge variant="outline">
                    {selectedCompletion.completion_type}
                  </Badge>
                  <Badge
                    variant="outline"
                    className={getConfidenceColor(
                      selectedCompletion.confidence
                    )}
                  >
                    {(selectedCompletion.confidence * 100).toFixed(0)}%
                    confidence
                  </Badge>
                </div>
                <p className="text-sm text-gray-600">
                  {selectedCompletion.description}
                </p>
              </div>
            </div>

            {selectedCompletion.architectural_context && (
              <div>
                <h4 className="text-sm font-medium mb-1">
                  Architectural Context
                </h4>
                <p className="text-sm text-blue-600">
                  {selectedCompletion.architectural_context}
                </p>
              </div>
            )}

            {selectedCompletion.pattern_type && (
              <div>
                <h4 className="text-sm font-medium mb-1">Pattern Type</h4>
                <Badge className="bg-purple-100 text-purple-800">
                  {selectedCompletion.pattern_type}
                </Badge>
              </div>
            )}

            {selectedCompletion.imports_needed &&
              selectedCompletion.imports_needed.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium mb-1">Required Imports</h4>
                  <div className="flex flex-wrap gap-1">
                    {selectedCompletion.imports_needed.map((imp, index) => (
                      <Badge key={index} variant="outline" className="text-xs">
                        {imp}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

            {selectedCompletion.usage_examples &&
              selectedCompletion.usage_examples.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium mb-1">Usage Examples</h4>
                  <div className="space-y-1">
                    {selectedCompletion.usage_examples.map((example, index) => (
                      <div
                        key={index}
                        className="bg-gray-50 p-2 rounded text-xs font-mono"
                      >
                        {example}
                      </div>
                    ))}
                  </div>
                </div>
              )}

            <div className="flex items-center gap-2">
              <Button
                size="sm"
                onClick={() => handleApplyCompletion(selectedCompletion)}
                className="flex items-center gap-2"
              >
                <Check className="h-4 w-4" />
                Apply Completion
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  setShowCompletions(false);
                  setCompletions([]);
                  setSelectedCompletion(null);
                }}
                className="flex items-center gap-2"
              >
                <X className="h-4 w-4" />
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Loading State */}
      {isLoading && (
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
              Generating semantic completions...
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};
