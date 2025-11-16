import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export interface Trace {
  id: string;
  message: string;
}

interface TracePanelProps {
  traces?: Trace[];
  isLoading?: boolean;
  error?: string;
}

export function TracePanel({ traces = [], isLoading = false, error }: TracePanelProps) {
  if (isLoading) {
    return (
      <Card className="bg-black border-2 border-[#00FF41]">
        <CardContent className="text-center text-[#00FF41]/70">LOADING_TRACES...</CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="bg-black border-2 border-[#FF0040]">
        <CardContent className="text-center text-[#FF0040]">ERROR: {error}</CardContent>
      </Card>
    );
  }

  if (!traces.length) {
    return (
      <Card className="bg-black border-2 border-[#00FF41]">
        <CardContent className="text-center text-[#00FF41]/70">NO_TRACES_AVAILABLE</CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-black border-2 border-[#00FF41]">
      <CardHeader>
        <CardTitle className="text-[#00FF41] font-black">TRACE_LOG</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {traces.map((trace) => (
          <div key={trace.id} className="font-mono text-sm text-[#00FF41]/90">
            {trace.message}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

export default TracePanel;
