import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { PermaGraphControlPanel } from '@/components/PermaGraphControlPanel';

export default function PermaGraphPage() {
  const [projectId, setProjectId] = useState('');
  const [kthuluPath, setKthuluPath] = useState('');

  return (
    <div className="p-4 space-y-4">
      <Card className="max-w-xl">
        <CardHeader>
          <CardTitle>PermaGraph Control Panel</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="projectId">Project ID</Label>
            <Input
              id="projectId"
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="kthuluPath">Kthulu Path</Label>
            <Input
              id="kthuluPath"
              value={kthuluPath}
              onChange={(e) => setKthuluPath(e.target.value)}
            />
          </div>
        </CardContent>
      </Card>
      {projectId && (
        <PermaGraphControlPanel
          projectId={projectId}
          kthuluPath={kthuluPath || undefined}
        />
      )}
    </div>
  );
}
