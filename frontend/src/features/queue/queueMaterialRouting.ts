// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import type {
  CapabilityDescriptor,
  MaterialSlotSnapshot,
  PrintArtifactFormat,
  PrinterViewModel,
} from '../../domain';
import type {
  ArtifactPrintPlan,
  MaterialBindingIntent,
  PrintPlanMaterialRequirement,
  PrintPlanPlate,
} from './queueCommandClient';

export interface MaterialSourceOption {
  slot: MaterialSlotSnapshot;
  unitLabel: string;
  slotLabel: string;
}

export type MaterialCompatibility = 'match' | 'unknown' | 'mismatch' | 'unconstrained';
export type RouteReadiness = 'ready' | 'stale' | 'unknown' | 'ambiguous' | 'incompatible';

export interface RoutePreview {
  state: RouteReadiness;
  toolheadLabels: string[];
}

export function printExecutionCapability(printer: PrinterViewModel | undefined): CapabilityDescriptor | undefined {
  return printer?.capabilities.find(
    (capability) => capability.capabilityId === 'foxforge.print_execution' && capability.majorVersion === 1,
  );
}

export function artifactFormatFromFilename(filename: string): PrintArtifactFormat | undefined {
  const normalized = filename.trim().toLowerCase();
  if (normalized.endsWith('.3mf')) return '3mf';
  if (normalized.endsWith('.gcode')) return 'gcode';
  return undefined;
}

export function printerAcceptsFormat(
  printer: PrinterViewModel | undefined,
  format: PrintArtifactFormat | undefined,
): boolean {
  if (!printer || !format) return false;
  const capability = printExecutionCapability(printer);
  if (!capability) return false;
  return capability.acceptedFormats?.includes(format) ?? true;
}

export function requiresExplicitMaterialRouting(
  printer: PrinterViewModel | undefined,
  format: PrintArtifactFormat | undefined,
): boolean {
  if (format !== '3mf') return false;
  return printExecutionCapability(printer)?.supportsMaterialBindings === true;
}

export function loadedMaterialSources(printer: PrinterViewModel | undefined): MaterialSourceOption[] {
  const system = printer?.materialSystem;
  if (!system) return [];
  return [...system.units]
    .sort((left, right) => left.position - right.position)
    .flatMap((unit) =>
      [...unit.slots]
        .sort((left, right) => left.position - right.position)
        .filter((slot) => slot.presence === 'loaded')
        .map((slot) => ({
          slot,
          unitLabel: unit.label ?? unit.unitId,
          slotLabel: slot.label ?? `${unit.label ?? unit.unitId} · ${slot.position + 1}`,
        })),
    );
}

export function materialCompatibility(
  requirement: PrintPlanMaterialRequirement,
  slot: MaterialSlotSnapshot,
): MaterialCompatibility {
  const expected = normalizeFamily(requirement.materialFamily);
  if (!expected) return 'unconstrained';
  const actual = normalizeFamily(slot.detectedMaterial?.materialFamily);
  if (!actual) return 'unknown';
  return actual === expected ? 'match' : 'mismatch';
}

export function routePreview(
  printer: PrinterViewModel | undefined,
  requirement: PrintPlanMaterialRequirement,
  slotId: string,
): RoutePreview {
  const topology = printer?.materialTopology;
  if (!topology || topology.stale || printer?.materialSystem?.stale) {
    return { state: 'stale', toolheadLabels: [] };
  }
  const route = topology.routes.find((candidate) => candidate.sourceSlotId === slotId);
  if (!route || route.kind === 'unknown' || route.toolheadIds.length === 0) {
    return { state: 'unknown', toolheadLabels: [] };
  }

  const toolheads = route.toolheadIds
    .map((toolheadId) => topology.toolheads.find((candidate) => candidate.toolheadId === toolheadId))
    .filter((toolhead): toolhead is NonNullable<typeof toolhead> => toolhead !== undefined);
  if (toolheads.length !== route.toolheadIds.length) {
    return { state: 'unknown', toolheadLabels: toolheads.map(toolheadLabel) };
  }

  const expectedPosition = requirement.expectedToolheadPosition;
  if (expectedPosition !== null) {
    const expected = topology.toolheads.filter((toolhead) => toolhead.position === expectedPosition);
    if (expected.length !== 1) {
      return { state: expected.length === 0 ? 'unknown' : 'ambiguous', toolheadLabels: toolheads.map(toolheadLabel) };
    }
    if (!route.toolheadIds.includes(expected[0].toolheadId)) {
      return { state: 'incompatible', toolheadLabels: toolheads.map(toolheadLabel) };
    }
    return { state: 'ready', toolheadLabels: [toolheadLabel(expected[0])] };
  }

  if (route.toolheadIds.length !== 1) {
    return { state: 'ambiguous', toolheadLabels: toolheads.map(toolheadLabel) };
  }
  return { state: 'ready', toolheadLabels: [toolheadLabel(toolheads[0])] };
}

export function selectedPlate(plan: ArtifactPrintPlan | undefined, plateIndex: number | undefined): PrintPlanPlate | undefined {
  if (!plan) return undefined;
  if (plateIndex !== undefined) return plan.plates.find((plate) => plate.plateIndex === plateIndex);
  return plan.plates.length === 1 ? plan.plates[0] : undefined;
}

export function routingReviewReady(options: {
  printer: PrinterViewModel | undefined;
  plan: ArtifactPrintPlan | undefined;
  plateIndex: number | undefined;
  bindings: MaterialBindingIntent[];
}): boolean {
  const { printer, plan, plateIndex, bindings } = options;
  const plate = selectedPlate(plan, plateIndex);
  if (!printer || !plan || !plate || !plate.readyForRouting) return false;

  const unsafeIssue = plan.issues.some((issue) => (
    (issue.plateIndex === null || issue.plateIndex === plate.plateIndex)
    && (issue.severity === 'blocking' || issue.code === 'toolhead_metadata_invalid')
  ));
  if (unsafeIssue) return false;

  if (!printer.materialSystem || !printer.materialTopology) return false;
  if (printer.materialSystem.stale || printer.materialTopology.stale) return false;

  const sources = loadedMaterialSources(printer);
  const byMaterial = new Map(bindings.map((binding) => [binding.materialIndex, binding.slotId]));
  if (byMaterial.size !== plate.materialRequirements.length) return false;

  return plate.materialRequirements.every((requirement) => {
    const slotId = byMaterial.get(requirement.materialIndex);
    if (!slotId) return false;
    const source = sources.find((candidate) => candidate.slot.slotId === slotId);
    if (!source) return false;
    const compatibility = materialCompatibility(requirement, source.slot);
    if (compatibility === 'mismatch' || compatibility === 'unknown') return false;
    return routePreview(printer, requirement, slotId).state === 'ready';
  });
}

function normalizeFamily(value: string | null | undefined): string | undefined {
  const normalized = value?.trim().toLocaleLowerCase();
  return normalized || undefined;
}

function toolheadLabel(toolhead: NonNullable<PrinterViewModel['materialTopology']>['toolheads'][number]): string {
  return toolhead.label ?? `Toolhead ${toolhead.position}`;
}
