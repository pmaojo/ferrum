export enum GraphStreamEventType {
  NODE_ADDED = 'NODE_ADDED',
  EDGE_ADDED = 'EDGE_ADDED',
  PATH_HIGHLIGHTED = 'PATH_HIGHLIGHTED',
  COMMUNITY_UPDATED = 'COMMUNITY_UPDATED',
}

export interface GraphStreamEvent {
  event_type: GraphStreamEventType;
  data: any;
  timestamp: string;
  kg_id: string;
  tenant_id: string;
}

type SendCallback = (payload: GraphStreamEvent | GraphStreamEvent[]) => void;

interface RegisterClientOpts {
  tenant_id: string;
  client_id: string;
  send: SendCallback;
}

interface UnregisterClientOpts {
  tenant_id: string;
  client_id: string;
}

/**
 * Minimal in-memory implementation inspired by PermaGraph's
 * WebSocketGraphStreamAdapter. It manages registered clients and
 * dispatches graph stream events to them via callbacks.
 */
export class WebSocketGraphStreamAdapter {
  private clients: Map<string, Map<string, SendCallback>> = new Map();

  register_client(opts: RegisterClientOpts): void {
    const tenant = this.clients.get(opts.tenant_id) ?? new Map();
    tenant.set(opts.client_id, opts.send);
    this.clients.set(opts.tenant_id, tenant);
  }

  unregister_client(opts: UnregisterClientOpts): void {
    const tenant = this.clients.get(opts.tenant_id);
    if (!tenant) return;
    tenant.delete(opts.client_id);
    if (tenant.size === 0) {
      this.clients.delete(opts.tenant_id);
    }
  }

  send_event(event: GraphStreamEvent): void {
    const tenant = this.clients.get(event.tenant_id);
    if (!tenant) return;
    for (const send of tenant.values()) {
      send(event);
    }
  }

  send_batch(events: GraphStreamEvent[]): void {
    const byTenant: Record<string, GraphStreamEvent[]> = {};
    for (const event of events) {
      byTenant[event.tenant_id] ??= [];
      byTenant[event.tenant_id].push(event);
    }
    for (const tenantId of Object.keys(byTenant)) {
      const tenant = this.clients.get(tenantId);
      if (!tenant) continue;
      const batch = byTenant[tenantId];
      for (const send of tenant.values()) {
        send(batch);
      }
    }
  }
}
