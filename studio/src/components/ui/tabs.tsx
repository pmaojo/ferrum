import { useState, type PropsWithChildren } from "react";

interface TabsProps {
  /** Initially selected tab */
  defaultValue: string;
}

/** Container for tabbed interface */
export function Tabs({ defaultValue, children }: PropsWithChildren<TabsProps>) {
  const [value] = useState(defaultValue);
  return <div data-tabs="" data-value={value}>{children}</div>;
}

interface TriggerProps {
  value: string;
}

/** Wrapper for tab triggers */
export function TabsList({ children }: PropsWithChildren<object>) {
  return <div className="flex gap-2 border-b mb-2">{children}</div>;
}

/** Clickable element selecting a tab */
export function TabsTrigger({ value, children }: PropsWithChildren<TriggerProps>) {
  return (
    <button className="px-2" data-tabs-trigger value={value}>
      {children}
    </button>
  );
}

/** Container for tab content */
export function TabsContent({ children }: PropsWithChildren<TriggerProps>) {
  return <div data-tabs-content>{children}</div>;
}
