import { useState, type PropsWithChildren } from "react";

interface TabsProps {
  defaultValue: string;
}

export function Tabs({ defaultValue, children }: PropsWithChildren<TabsProps>) {
  const [value] = useState(defaultValue);
  return <div data-tabs="" data-value={value}>{children}</div>;
}

interface TriggerProps {
  value: string;
}

export function TabsList({ children }: PropsWithChildren<{}>) {
  return <div className="flex gap-2 border-b mb-2">{children}</div>;
}

export function TabsTrigger({ value, children }: PropsWithChildren<TriggerProps>) {
  return (
    <button className="px-2" data-tabs-trigger value={value}>
      {children}
    </button>
  );
}

export function TabsContent({ children }: PropsWithChildren<TriggerProps>) {
  return <div data-tabs-content>{children}</div>;
}
