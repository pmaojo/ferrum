import { Edge } from 'reactflow';

export const EdgeTypes = {
  default: 'default',
  straight: 'straight',
  step: 'step',
  smoothstep: 'smoothstep',
  simplebezier: 'simplebezier',
};

export const defaultEdgeOptions = {
  type: 'default',
  animated: false,
  style: {
    stroke: '#00FF41',
    strokeWidth: 2,
  },
};

export type CustomEdgeData = {
  label?: string;
  type?: string;
  animated?: boolean;
};

export type CustomEdge = Edge<CustomEdgeData>;
