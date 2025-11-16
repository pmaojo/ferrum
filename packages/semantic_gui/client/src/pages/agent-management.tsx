import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { AgentManagementDashboard } from '@/components/agents/AgentManagementDashboard';

export default function AgentManagementPage() {
  const [projectId, setProjectId] = useState('');

  return (
    <div className="p-4 space-y-4">
      <Card className="max-w-xl">
        <CardHeader>
          <CardTitle>Agent Management Dashboard</CardTitle>
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
        </CardContent>
      </Card>
      {projectId && <AgentManagementDashboard projectId={projectId} />}
    </div>
  );
}
