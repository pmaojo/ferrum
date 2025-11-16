import { memo, useState } from 'react';
import { EdgeProps, getBezierPath } from 'reactflow';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Info, X, ArrowRight, Settings } from 'lucide-react';

interface ConnectionEdgeProps extends EdgeProps {
  onDoubleClick?: (edge: any) => void;
}

export const ConnectionEdge = memo(
  ({
    id,
    sourceX,
    sourceY,
    targetX,
    targetY,
    data,
    source,
    target,
    onDoubleClick,
  }: ConnectionEdgeProps) => {
    const [showDetails, setShowDetails] = useState(false);
    const [edgePath, labelX, labelY] = getBezierPath({
      sourceX,
      sourceY,
      targetX,
      targetY,
    });

    const parameters = data?.parameters || [];
    const methodCalls = data?.methodCalls || [];
    const hasDetails = parameters.length > 0 || methodCalls.length > 0;

    const stroke = data?.violationMessage
      ? '#ff0000'
      : data?.strokeColor || '#00FF41';

    return (
      <>
        <path
          id={id}
          style={{ stroke, strokeWidth: 2 }}
          className="react-flow__edge-path cursor-pointer"
          d={edgePath}
          onDoubleClick={(e) => {
            e.stopPropagation();
            if (onDoubleClick) {
              onDoubleClick({ id, source, target, data });
            }
          }}
        >
          {data?.violationMessage && <title>{data.violationMessage}</title>}
        </path>

        {/* Edge Label with Parameter Count */}
        <g transform={`translate(${labelX}, ${labelY})`}>
          <rect
            x="-25"
            y="-8"
            width="50"
            height="16"
            fill="#000"
            stroke={stroke}
            strokeWidth="1"
            rx="3"
          />
          <text
            className="react-flow__edge-text"
            style={{
              fill: stroke,
              fontSize: '8px',
              fontFamily: 'monospace',
              textAnchor: 'middle',
              dominantBaseline: 'middle',
            }}
          >
            {data?.type?.toUpperCase() || 'LINK'}
          </text>

          {hasDetails && (
            <circle
              cx="30"
              cy="0"
              r="6"
              fill="#00FFFF"
              stroke="#000"
              strokeWidth="1"
              className="cursor-pointer"
              onClick={(e) => {
                e.stopPropagation();
                setShowDetails(true);
              }}
            />
          )}

          {hasDetails && (
            <text
              x="30"
              y="0"
              style={{
                fill: '#000',
                fontSize: '8px',
                fontFamily: 'monospace',
                textAnchor: 'middle',
                dominantBaseline: 'middle',
                pointerEvents: 'none',
              }}
            >
              {parameters.length + methodCalls.length}
            </text>
          )}
        </g>

        {/* Parameter Details Modal */}
        {showDetails && (
          <foreignObject
            x={labelX + 40}
            y={labelY - 100}
            width="300"
            height="200"
          >
            <Card className="bg-black border-2 border-[#00FFFF] text-[#00FF41] shadow-lg">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm text-[#00FFFF] tracking-wider">
                    CONNECTION_DETAILS
                  </CardTitle>
                  <Button
                    onClick={() => setShowDetails(false)}
                    variant="outline"
                    size="sm"
                    className="h-6 w-6 p-0 border-[#FF00FF] text-[#FF00FF]"
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="text-xs max-h-32 overflow-y-auto">
                {/* Parameters Section */}
                {parameters.length > 0 && (
                  <div className="mb-3">
                    <div className="text-[#00FFFF] font-bold mb-1 flex items-center">
                      <Settings className="h-3 w-3 mr-1" />
                      PARAMETERS ({parameters.length})
                    </div>
                    <div className="space-y-1">
                      {parameters.map((param: any, idx: number) => (
                        <div
                          key={idx}
                          className="flex items-center justify-between text-xs"
                        >
                          <span className="text-[#00FF41]">{param.name}</span>
                          <div className="flex items-center space-x-1">
                            <Badge
                              variant="outline"
                              className="text-xs h-4 border-[#FFFF00] text-[#FFFF00]"
                            >
                              {param.dataType || param.type}
                            </Badge>
                            {param.direction && (
                              <ArrowRight className="h-2 w-2 text-[#00FFFF]" />
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Method Calls Section */}
                {methodCalls.length > 0 && (
                  <div>
                    <div className="text-[#00FFFF] font-bold mb-1 flex items-center">
                      <Info className="h-3 w-3 mr-1" />
                      METHODS ({methodCalls.length})
                    </div>
                    <div className="space-y-1">
                      {methodCalls.map((method: any, idx: number) => (
                        <div key={idx} className="text-[#00FF41]">
                          <div className="font-mono">{method.methodName}()</div>
                          {method.parameters &&
                            method.parameters.length > 0 && (
                              <div className="text-[#00FF41]/70 text-xs ml-2">
                                params: {method.parameters.join(', ')}
                              </div>
                            )}
                          {method.returnType && (
                            <div className="text-[#FFFF00] text-xs ml-2">
                              → {method.returnType}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </foreignObject>
        )}
      </>
    );
  }
);
