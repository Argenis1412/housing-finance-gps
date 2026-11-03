/** Exact display only: never convert financial values to binary numbers. */
export function money(value: string): string {
  if (!/^-?(?:0|[1-9][0-9]*)\.[0-9]{2}$/.test(value)) throw new Error("Invalid monetary response");
  const [integer, fraction] = value.split(".");
  return `R$ ${integer.replace(/\B(?=(\d{3})+(?!\d))/g, ".")},${fraction}`;
}
export const names = {sac: "SAC", price: "Price", rent: "Aluguel + investimento", consortium: "Consórcio"} as const;
export const phaseNames: Record<string, string> = {opening_allocation: "alocação inicial", external_expenses: "despesas externas", strategy_obligations: "obrigações da estratégia", investment_contribution: "aporte obrigatório"};
