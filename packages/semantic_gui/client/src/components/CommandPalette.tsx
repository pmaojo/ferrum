import * as React from 'react';
import { Command } from 'cmdk';
import Ajv from 'ajv';
import { useCommandPalette } from '@/hooks/useCommandPalette';
import { backgroundTaskManager } from '@/services/backgroundTaskManager';
import { kthuluService } from '@/services/kthuluService';
import { useCLIOperations, type CLIOperation } from '@/hooks/useCLIOperations';
import { useProject } from '@/hooks/use-graph';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from '@/components/ui/select';

interface CommandPaletteProps {
  projectId: string;
}

export function CommandPalette({ projectId }: CommandPaletteProps) {
  const { open, setOpen } = useCommandPalette();
  const { operations } = useCLIOperations(projectId);
  const { data: project } = useProject(projectId);
  const projectConfig = project?.metadata?.config || {};

  const [selectedOp, setSelectedOp] = React.useState<CLIOperation | null>(null);
  const [args, setArgs] = React.useState<Record<string, any>>({});
  const ajv = React.useMemo(() => new Ajv(), []);
  const validator = React.useMemo(() => {
    if (!selectedOp?.argsSchema) return null;
    return ajv.compile(selectedOp.argsSchema);
  }, [ajv, selectedOp]);

  const isValid = React.useMemo(() => {
    if (!validator) return true;
    return validator(args) as boolean;
  }, [validator, args]);

  const requiresInput = React.useCallback(
    (op: CLIOperation) => {
      const props = op.argsSchema?.properties;
      if (!props) return false;
      return Object.entries<any>(props).some(([key, v]) => {
        if ('const' in v) return false;
        return projectConfig[key] === undefined;
      });
    },
    [projectConfig]
  );

  const handleSelect = React.useCallback(
    (operation: CLIOperation) => {
      setOpen(false);
      if (requiresInput(operation)) {
        const initial: Record<string, any> = { ...projectConfig };
        const props = operation.argsSchema?.properties || {};
        for (const [key, schema] of Object.entries<any>(props)) {
          if ('const' in schema) continue;
          if (initial[key] !== undefined) continue;
          if (schema.default !== undefined) initial[key] = schema.default;
          else if (schema.type === 'boolean') initial[key] = false;
          else initial[key] = '';
        }
        setArgs(initial);
        setSelectedOp(operation);
      } else {
        backgroundTaskManager.submitTask(
          `cli:${operation.key}`,
          'cli_command',
          async () => {
            await kthuluService.executeCommand(projectId, operation.key);
          }
        );
      }
    },
    [projectId, requiresInput, setOpen, projectConfig]
  );

  const renderField = (name: string, schema: any) => {
    if (schema.enum) {
      return (
        <Select
          value={args[name] ?? ''}
          onValueChange={(v) => setArgs((prev) => ({ ...prev, [name]: v }))}
        >
          <SelectTrigger>
            <SelectValue placeholder="Select" />
          </SelectTrigger>
          <SelectContent>
            {schema.enum.map((val: any) => (
              <SelectItem key={val} value={String(val)}>
                {String(val)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      );
    }
    if (schema.type === 'boolean') {
      return (
        <Checkbox
          checked={!!args[name]}
          onCheckedChange={(v) =>
            setArgs((prev) => ({ ...prev, [name]: v === true }))
          }
        />
      );
    }
    const inputType =
      schema.type === 'number' || schema.type === 'integer' ? 'number' : 'text';
    return (
      <Input
        id={name}
        type={inputType}
        value={args[name] ?? ''}
        onChange={(e) =>
          setArgs((prev) => ({
            ...prev,
            [name]:
              inputType === 'number' ? Number(e.target.value) : e.target.value,
          }))
        }
      />
    );
  };

  const runSelected = React.useCallback(async () => {
    if (!selectedOp) return;
    if (validator && !validator(args)) return;
    const op = selectedOp;
    setSelectedOp(null);
    const argArray = Object.entries(args).flatMap(([k, v]) => {
      if (v === '' || v === undefined || v === false) return [];
      if (typeof v === 'boolean') return [`--${k}`];
      return [`--${k}`, String(v)];
    });
    await backgroundTaskManager.submitTask(
      `cli:${op.key}`,
      'cli_command',
      async () => {
        await kthuluService.executeCommand(projectId, op.key, argArray);
      }
    );
  }, [args, projectId, selectedOp, validator]);

  return (
    <>
      <Command.Dialog
        open={open}
        onOpenChange={setOpen}
        label="Command Palette"
      >
        <Command.Input placeholder="Type a command..." />
        <Command.List>
          <Command.Empty>No results found.</Command.Empty>
          {operations.map((op) => (
            <Command.Item
              key={op.key}
              value={op.key}
              onSelect={() => handleSelect(op)}
            >
              <div className="flex flex-col">
                <span>{op.label}</span>
                {op.description && (
                  <span className="text-xs text-muted-foreground">
                    {op.description}
                  </span>
                )}
              </div>
            </Command.Item>
          ))}
        </Command.List>
      </Command.Dialog>

      <Dialog
        open={!!selectedOp}
        onOpenChange={(o) => !o && setSelectedOp(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{selectedOp?.label}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            {selectedOp &&
              Object.entries<any>(selectedOp.argsSchema?.properties || {}).map(
                ([key, schema]) => {
                  if ('const' in schema) return null;
                  if (projectConfig[key] !== undefined) return null;
                  return (
                    <div key={key} className="space-y-2">
                      <Label htmlFor={key}>{key}</Label>
                      {renderField(key, schema)}
                    </div>
                  );
                }
              )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSelectedOp(null)}>
              Cancel
            </Button>
            <Button onClick={runSelected} disabled={!isValid}>
              Execute
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

export default CommandPalette;
