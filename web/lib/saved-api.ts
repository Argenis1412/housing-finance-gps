import type {components} from "./api.generated";
import {readResponse, validateResult} from "./api";

export type SavedResult = components["schemas"]["SavedComparisonV1"];
export type SavedList = components["schemas"]["SavedComparisonListV1"];
type Creation = components["schemas"]["ComparisonCreationRequestV1"];
const base = "/api/v1/comparison/saved-simulations";
const id = (value: unknown): value is string => typeof value === "string" && /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(value);
const timestamp = (value: unknown): value is string => typeof value === "string" && /^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$/.test(value);
const object = (value: unknown): value is Record<string, unknown> => value !== null && typeof value === "object" && !Array.isArray(value);
function check(value: unknown): asserts value {if (!value) throw new Error("invalid_response");}
function locator(value: string): string {
  return id(value) ? value : "~" + btoa(Array.from(new TextEncoder().encode(value), byte => String.fromCharCode(byte)).join("")).replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/, "");
}

async function request(path: string, init: RequestInit = {}, signal?: AbortSignal): Promise<unknown> {
  const timeout = new AbortController();
  const active = signal ? AbortSignal.any([signal, timeout.signal]) : timeout.signal;
  const timer = setTimeout(() => timeout.abort(new Error("timeout")), 30_000);
  try {
    let response: Response;
    try {response = await fetch(path, {...init, cache: "no-store", signal: active});}
    catch {if (active.aborted) throw active.reason; throw new Error("network_error");}
    if (init.method === "DELETE" && response.status === 204) return null;
    const value = await readResponse(response);
    check(init.method === "POST" ? response.status === 200 || response.status === 201 : response.status === 200);
    return value;
  } finally {clearTimeout(timer);}
}
function validateSaved(value: unknown, expected: string): SavedResult {
  check(object(value) && value.api_version === "v1" && value.kind === "saved_comparison" && id(value.simulation_id) && value.simulation_id === expected && timestamp(value.saved_at));
  validateResult(value.result);
  return value as SavedResult;
}
export async function createSaved(operationId: string, comparison: Creation, signal: AbortSignal): Promise<SavedResult> {
  return validateSaved(await request(base, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({...comparison, operation_id: operationId})}, signal), operationId);
}
export async function readSaved(simulationId: string, signal: AbortSignal): Promise<SavedResult> {
  return validateSaved(await request(`${base}/${locator(simulationId)}`, {}, signal), simulationId);
}
export async function listSaved(offset: number, signal: AbortSignal): Promise<SavedList> {
  const value = await request(`${base}?limit=20&offset=${offset}`, {}, signal);
  check(object(value) && value.api_version === "v1" && value.kind === "saved_comparison_list" && Array.isArray(value.items) && value.items.length <= 20);
  value.items.forEach(item => check(object(item) && typeof item.simulation_id === "string" && typeof item.saved_at === "string"));
  check(value.next_offset === null || (Number.isSafeInteger(value.next_offset) && (value.next_offset as number) > offset));
  return value as SavedList;
}
export async function deleteSaved(simulationId: string, signal: AbortSignal): Promise<void> {
  check(await request(`${base}/${locator(simulationId)}`, {method: "DELETE"}, signal) === null);
}
export function uncertainSave(error: unknown): boolean {
  return !(error instanceof Error) || ["network_error", "timeout", "invalid_response", "incompatible_response", "response_too_large"].includes(error.message) || error.name === "AbortError" || error.name === "TypeError";
}

/** Index metadata is unverified; an illegible time must not hide deletable records. */
export function displaySavedTime(value: string): string {
  const date = new Date(value);
  return timestamp(value) && Number.isFinite(date.getTime()) && date.toISOString().replace(".000Z", "Z") === value ? value : "Data de gravação ilegível";
}
