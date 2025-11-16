import { Switch, Route } from 'wouter';
import { queryClient } from './lib/queryClient';
import { QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from '@/components/ui/toaster';
import { TooltipProvider } from '@/components/ui/tooltip';
import GraphEditor from '@/pages/graph-editor';
import TemplateMarketplace from '@/pages/template-marketplace';
import PermaGraphPage from '@/pages/permagraph';
import AgentManagementPage from '@/pages/agent-management';
import UnifiedDashboard from '@/pages/unified-dashboard';
import NotFound from '@/pages/not-found';
import { useEffect } from 'react';
import { useFMSounds } from '@/hooks/useFMSounds';
import { MainNavigationMenu } from '@/components/NavigationMenu';

function Router() {
  return (
    <Switch>
      <Route path="/" component={GraphEditor} />
      <Route path="/dashboard" component={UnifiedDashboard} />
      <Route path="/templates" component={TemplateMarketplace} />
      <Route path="/permagraph" component={PermaGraphPage} />
      <Route path="/agents" component={AgentManagementPage} />
      <Route component={NotFound} />
    </Switch>
  );
}

function App() {
  const { playBoot } = useFMSounds(0.8);

  useEffect(() => {
    // Delay boot sound to avoid autoplay restrictions
    const timer = setTimeout(() => {
      playBoot();
    }, 500);
    return () => clearTimeout(timer);
  }, [playBoot]);

  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <div className="min-h-screen bg-background text-foreground scan-lines terminal-flicker">
          <Toaster />
          <MainNavigationMenu />
          <Router />
        </div>
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;
