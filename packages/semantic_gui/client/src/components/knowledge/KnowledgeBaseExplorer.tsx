import React, { useState } from 'react';
import { useKnowledgeBase } from '@/hooks/useKnowledgeBase';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';

/**
 * Simple explorer component that leverages the knowledge base hooks to
 * perform searches and display patterns and best practices.
 */
const KnowledgeBaseExplorer: React.FC = () => {
  const {
    search,
    listPatterns,
    listPractices,
    searchResults,
    patterns,
    practices,
    loading,
    error,
  } = useKnowledgeBase();
  const [query, setQuery] = useState('');

  const handleSearch = () =>
    search({ queryType: 'architectural_guidance', queryText: query });
  const handlePatterns = () => listPatterns({ search: query });
  const handlePractices = () => listPractices({ search: query });

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search knowledge base"
        />
        <Button onClick={handleSearch} disabled={loading}>
          Search
        </Button>
        <Button variant="outline" onClick={handlePatterns} disabled={loading}>
          Patterns
        </Button>
        <Button variant="outline" onClick={handlePractices} disabled={loading}>
          Practices
        </Button>
      </div>

      {error && (
        <Card>
          <CardContent>
            <p className="text-destructive">{error}</p>
          </CardContent>
        </Card>
      )}

      {searchResults.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Search Results</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="list-disc pl-5 space-y-1">
              {searchResults.map((r: any, idx) => (
                <li key={idx}>
                  {r.title || r.name || r.id || JSON.stringify(r)}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {patterns.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Patterns</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="list-disc pl-5 space-y-1">
              {patterns.map((p: any) => (
                <li key={p.id || p.name}>{p.name || p.title || p.id}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {practices.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Practices</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="list-disc pl-5 space-y-1">
              {practices.map((p: any) => (
                <li key={p.id || p.name}>{p.name || p.title || p.id}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default KnowledgeBaseExplorer;
