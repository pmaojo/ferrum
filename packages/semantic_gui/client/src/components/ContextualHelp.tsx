import { Card, CardContent } from '@/components/ui/card';

interface ContextualHelpProps {
  state: 'no-ontology' | 'no-graph' | 'initialized';
}

const tips: Record<ContextualHelpProps['state'], string> = {
  'no-ontology':
    'Sincroniza para importar la ontología desde tu proyecto Kthulu.',
  'no-graph':
    'Refresca para generar el grafo semántico a partir de la ontología.',
  initialized: 'El motor semántico está listo para analizar tu arquitectura.',
};

export function ContextualHelp({ state }: ContextualHelpProps) {
  const tip = tips[state];
  if (!tip) return null;
  return (
    <Card className="mt-4">
      <CardContent className="text-sm text-muted-foreground">{tip}</CardContent>
    </Card>
  );
}
