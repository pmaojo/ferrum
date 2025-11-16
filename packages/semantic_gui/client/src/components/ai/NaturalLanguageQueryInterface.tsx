import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  Mic,
  MicOff,
  Loader2,
  Lightbulb,
  History,
  X,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { useToast } from '@/hooks/use-toast';

interface QueryResponse {
  session_id: string;
  query: string;
  query_type: string;
  response: string;
  structured_data: any;
  confidence: number;
  suggestions: string[];
  related_components: Array<{
    iri: string;
    name: string;
    type: string;
    module: string;
  }>;
  timestamp: string;
}

interface QueryHistory {
  query: string;
  response: string;
  timestamp: string;
  confidence: number;
}

interface NaturalLanguageQueryInterfaceProps {
  onComponentSelect?: (component: any) => void;
  className?: string;
}

export const NaturalLanguageQueryInterface: React.FC<
  NaturalLanguageQueryInterfaceProps
> = ({ onComponentSelect, className = '' }) => {
  const [query, setQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [currentResponse, setCurrentResponse] = useState<QueryResponse | null>(
    null
  );
  const [queryHistory, setQueryHistory] = useState<QueryHistory[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [sessionId, setSessionId] = useState<string>('');

  const inputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();

  // Initialize session
  useEffect(() => {
    setSessionId(`session_${Date.now()}`);
  }, []);

  // Get query suggestions as user types
  useEffect(() => {
    if (query.length > 2) {
      fetchQuerySuggestions(query);
    } else {
      setSuggestions([]);
    }
  }, [query]);

  const fetchQuerySuggestions = async (partialQuery: string) => {
    try {
      const response = await fetch('/api/ai/query-suggestions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ partial_query: partialQuery }),
      });

      if (response.ok) {
        const data = await response.json();
        setSuggestions(data.suggestions || []);
      }
    } catch (error) {
      console.error('Error fetching suggestions:', error);
    }
  };

  const handleSubmitQuery = async (queryText: string = query) => {
    if (!queryText.trim()) return;

    setIsLoading(true);
    setCurrentResponse(null);

    try {
      const response = await fetch('/api/ai/natural-language-query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: queryText,
          session_id: sessionId,
          context: {
            timestamp: new Date().toISOString(),
            source: 'scg_ui',
          },
        }),
      });

      if (response.ok) {
        const data: QueryResponse = await response.json();
        setCurrentResponse(data);

        // Add to history
        const historyItem: QueryHistory = {
          query: queryText,
          response: data.response,
          timestamp: data.timestamp,
          confidence: data.confidence,
        };
        setQueryHistory((prev) => [historyItem, ...prev.slice(0, 9)]); // Keep last 10

        // Clear input
        setQuery('');
        setSuggestions([]);

        toast({
          title: 'Query processed',
          description: `Found response with ${(data.confidence * 100).toFixed(0)}% confidence`,
        });
      } else {
        throw new Error('Failed to process query');
      }
    } catch (error) {
      console.error('Error processing query:', error);
      toast({
        title: 'Query failed',
        description: 'Failed to process your query. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleVoiceInput = () => {
    if (
      !('webkitSpeechRecognition' in window) &&
      !('SpeechRecognition' in window)
    ) {
      toast({
        title: 'Voice input not supported',
        description: "Your browser doesn't support voice input.",
        variant: 'destructive',
      });
      return;
    }

    const SpeechRecognition =
      (window as any).webkitSpeechRecognition ||
      (window as any).SpeechRecognition;
    const recognition = new SpeechRecognition();

    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
      setIsListening(true);
    };

    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      setQuery(transcript);
      setIsListening(false);
    };

    recognition.onerror = () => {
      setIsListening(false);
      toast({
        title: 'Voice input error',
        description: 'Failed to capture voice input. Please try again.',
        variant: 'destructive',
      });
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognition.start();
  };

  const handleSuggestionClick = (suggestion: string) => {
    setQuery(suggestion);
    setSuggestions([]);
    inputRef.current?.focus();
  };

  const handleComponentClick = (component: any) => {
    if (onComponentSelect) {
      onComponentSelect(component);
    }
  };

  const getQueryTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      component_search: 'bg-blue-100 text-blue-800',
      relationship_analysis: 'bg-green-100 text-green-800',
      pattern_detection: 'bg-purple-100 text-purple-800',
      architecture_review: 'bg-orange-100 text-orange-800',
      code_suggestion: 'bg-yellow-100 text-yellow-800',
      anti_pattern_check: 'bg-red-100 text-red-800',
    };
    return colors[type] || 'bg-gray-100 text-gray-800';
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-600';
    if (confidence >= 0.6) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Query Input */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center gap-2">
            <Lightbulb className="h-5 w-5" />
            Natural Language Architecture Query
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="relative">
            <div className="flex gap-2">
              <div className="flex-1 relative">
                <Input
                  ref={inputRef}
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Ask about your architecture... (e.g., 'Find all components that depend on UserService')"
                  onKeyPress={(e) => e.key === 'Enter' && handleSubmitQuery()}
                  disabled={isLoading}
                  className="pr-10"
                />
                {query && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="absolute right-1 top-1 h-8 w-8 p-0"
                    onClick={() => setQuery('')}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                )}
              </div>
              <Button
                onClick={handleVoiceInput}
                variant="outline"
                size="icon"
                disabled={isLoading}
                className={isListening ? 'bg-red-50 border-red-200' : ''}
              >
                {isListening ? (
                  <MicOff className="h-4 w-4 text-red-600" />
                ) : (
                  <Mic className="h-4 w-4" />
                )}
              </Button>
              <Button
                onClick={() => handleSubmitQuery()}
                disabled={isLoading || !query.trim()}
                className="min-w-[100px]"
              >
                {isLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <>
                    <Send className="h-4 w-4 mr-2" />
                    Ask
                  </>
                )}
              </Button>
            </div>

            {/* Query Suggestions */}
            {suggestions.length > 0 && (
              <Card className="absolute top-full left-0 right-0 z-10 mt-1 max-h-48 overflow-hidden">
                <ScrollArea className="max-h-48">
                  <div className="p-2 space-y-1">
                    {suggestions.map((suggestion, index) => (
                      <button
                        key={index}
                        onClick={() => handleSuggestionClick(suggestion)}
                        className="w-full text-left p-2 text-sm hover:bg-gray-100 rounded transition-colors"
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                </ScrollArea>
              </Card>
            )}
          </div>

          {/* History Toggle */}
          <div className="flex justify-between items-center">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowHistory(!showHistory)}
              className="text-gray-600"
            >
              <History className="h-4 w-4 mr-2" />
              Query History ({queryHistory.length})
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Query History */}
      {showHistory && queryHistory.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Recent Queries</CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="max-h-48">
              <div className="space-y-2">
                {queryHistory.map((item, index) => (
                  <div
                    key={index}
                    className="p-2 border rounded-lg hover:bg-gray-50 cursor-pointer"
                    onClick={() => setQuery(item.query)}
                  >
                    <div className="text-sm font-medium truncate">
                      {item.query}
                    </div>
                    <div className="text-xs text-gray-500 flex items-center gap-2">
                      <span>
                        {new Date(item.timestamp).toLocaleTimeString()}
                      </span>
                      <span
                        className={`font-medium ${getConfidenceColor(item.confidence)}`}
                      >
                        {(item.confidence * 100).toFixed(0)}% confidence
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      )}

      {/* Current Response */}
      {currentResponse && (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg">Response</CardTitle>
              <div className="flex items-center gap-2">
                <Badge
                  className={getQueryTypeColor(currentResponse.query_type)}
                >
                  {currentResponse.query_type.replace('_', ' ')}
                </Badge>
                <Badge
                  variant="outline"
                  className={getConfidenceColor(currentResponse.confidence)}
                >
                  {(currentResponse.confidence * 100).toFixed(0)}% confidence
                </Badge>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Main Response */}
            <div className="prose prose-sm max-w-none">
              <p className="whitespace-pre-wrap">{currentResponse.response}</p>
            </div>

            {/* Related Components */}
            {currentResponse.related_components.length > 0 && (
              <div>
                <h4 className="font-medium mb-2">Related Components</h4>
                <div className="flex flex-wrap gap-2">
                  {currentResponse.related_components.map(
                    (component, index) => (
                      <Button
                        key={index}
                        variant="outline"
                        size="sm"
                        onClick={() => handleComponentClick(component)}
                        className="text-xs"
                      >
                        <span className="font-medium">{component.name}</span>
                        <span className="text-gray-500 ml-1">
                          ({component.type})
                        </span>
                      </Button>
                    )
                  )}
                </div>
              </div>
            )}

            {/* Suggestions */}
            {currentResponse.suggestions.length > 0 && (
              <div>
                <h4 className="font-medium mb-2">Suggestions</h4>
                <ul className="text-sm space-y-1">
                  {currentResponse.suggestions.map((suggestion, index) => (
                    <li key={index} className="flex items-start gap-2">
                      <span className="text-gray-400 mt-1">•</span>
                      <span>{suggestion}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Structured Data (if available) */}
            {currentResponse.structured_data &&
              Object.keys(currentResponse.structured_data).length > 0 && (
                <div>
                  <Separator className="my-4" />
                  <details className="text-sm">
                    <summary className="font-medium cursor-pointer hover:text-blue-600">
                      View Structured Data
                    </summary>
                    <pre className="mt-2 p-3 bg-gray-50 rounded-lg overflow-auto text-xs">
                      {JSON.stringify(currentResponse.structured_data, null, 2)}
                    </pre>
                  </details>
                </div>
              )}
          </CardContent>
        </Card>
      )}

      {/* Example Queries */}
      {!currentResponse && queryHistory.length === 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Example Queries</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {[
                'Find all components that depend on UserService',
                'Show me the architecture patterns in the auth module',
                'What are the anti-patterns in my code?',
                'List all use cases in the payment module',
                'Analyze the quality of my architecture',
                'Find circular dependencies',
              ].map((example, index) => (
                <Button
                  key={index}
                  variant="ghost"
                  size="sm"
                  onClick={() => handleSubmitQuery(example)}
                  className="text-left justify-start h-auto p-2 text-xs"
                  disabled={isLoading}
                >
                  {example}
                </Button>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};
