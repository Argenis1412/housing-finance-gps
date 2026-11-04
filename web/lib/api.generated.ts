export type ClosedJsonValue = { [key: string]: ClosedJsonValue } | ClosedJsonValue[] | string | number | boolean | null;

export interface paths {
    "/api/v1/comparison/saved-simulations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List unverified saved-comparison index metadata */
        get: operations["list_saved_api_v1_comparison_saved_simulations_get"];
        put?: never;
        /** Compare once and save complete local synthetic evidence */
        post: operations["create_saved_api_v1_comparison_saved_simulations_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/comparison/saved-simulations/{simulation_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read stored historical output without calculation or replay */
        get: operations["read_saved_api_v1_comparison_saved_simulations__simulation_id__get"];
        put?: never;
        post?: never;
        /** Delete evidence while retaining its opaque operation ID */
        delete: operations["delete_saved_api_v1_comparison_saved_simulations__simulation_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/comparison/simulations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Create a transient synthetic comparison v2 simulation
         * @description Creates sealed evidence internally. No persistence, retrieval, export or HTTP replay. Only rent invests.
         */
        post: operations["create_simulation_api_v1_comparison_simulations_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/financing/calculations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Calculate an ephemeral v3 financing projection
         * @description Returns a non-persistent calculation projection. It is not a simulation result and contains no data snapshot, canonical request, sealed outcome, timestamp, or replay claim.
         */
        post: operations["calculate_financing_projection_api_v1_financing_calculations_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /**
         * ApiErrorV1
         * @description Stable public error without internal domain diagnostic text.
         */
        ApiErrorV1: {
            /** Code */
            code: string;
            /** Message Pt Br */
            message_pt_br: string;
        };
        /**
         * CalculationProjectionV1
         * @description Versioned ephemeral calculation projection, distinct from a simulation result.
         */
        CalculationProjectionV1: {
            /**
             * Api Version
             * @constant
             */
            api_version: "v1";
            /** Comparison Ledger */
            comparison_ledger: components["schemas"]["ComparisonLedgerRowV1"][];
            /**
             * Contract Schema Version
             * @constant
             */
            contract_schema_version: "financing-replay-v3";
            /** Contractual Schedule */
            contractual_schedule: components["schemas"]["ContractualScheduleRowV1"][];
            /**
             * Engine Version
             * @constant
             */
            engine_version: "financing-centavo-safe-v3";
            /**
             * Ruleset Version
             * @constant
             */
            ruleset_version: "financing-ruleset-v2";
            /**
             * Strategy
             * @enum {string}
             */
            strategy: "sac" | "price";
        };
        /** ChildVersionsV1 */
        ChildVersionsV1: {
            /** Contract Schema Version */
            contract_schema_version: string;
            /** Engine Version */
            engine_version: string;
            /** Ruleset Version */
            ruleset_version: string;
        };
        "ClosedJsonValue-Input": ClosedJsonValue;
        "ClosedJsonValue-Output": ClosedJsonValue;
        /** ComparisonApiErrorV1 */
        ComparisonApiErrorV1: {
            /**
             * Api Version
             * @default v1
             * @constant
             */
            api_version: "v1";
            /** Code */
            code: string;
            /** Message Pt Br */
            message_pt_br: string;
        };
        /** ComparisonChildV1 */
        ComparisonChildV1: {
            /** Input Classification */
            input_classification?: {
                [key: string]: string;
            } | null;
            strategy: components["schemas"]["Strategy"];
            versions: components["schemas"]["ChildVersionsV1"];
        };
        /** ComparisonCreationRequestV1 */
        ComparisonCreationRequestV1: {
            comparison: components["schemas"]["ComparisonInputsV1-Input"];
        };
        /** ComparisonFailureV1 */
        ComparisonFailureV1: {
            code: components["schemas"]["FailureCategory"];
            /** Message Pt Br */
            message_pt_br: string;
            /** Month */
            month?: number | null;
            /** Phase */
            phase?: ("opening_allocation" | "external_expenses" | "strategy_obligations" | "investment_contribution") | null;
        };
        /**
         * ComparisonInputsV1
         * @description Six v2 fields, without coercion or premature child/global validation.
         *
         *     Expected shapes are defined by comparison-application-api-ui-v1.md and the
         *     retained monthly-resources contract. Malformed child values intentionally
         *     reach the domain so other alternatives can still be compared.
         */
        "ComparisonInputsV1-Input": {
            consortium: components["schemas"]["ClosedJsonValue-Input"];
            constraints: components["schemas"]["ClosedJsonValue-Input"];
            financing: components["schemas"]["ClosedJsonValue-Input"];
            monthly_resources: components["schemas"]["ClosedJsonValue-Input"];
            rent: components["schemas"]["ClosedJsonValue-Input"];
            shared: components["schemas"]["ClosedJsonValue-Input"];
        };
        /**
         * ComparisonInputsV1
         * @description Six v2 fields, without coercion or premature child/global validation.
         *
         *     Expected shapes are defined by comparison-application-api-ui-v1.md and the
         *     retained monthly-resources contract. Malformed child values intentionally
         *     reach the domain so other alternatives can still be compared.
         */
        "ComparisonInputsV1-Output": {
            consortium: components["schemas"]["ClosedJsonValue-Output"];
            constraints: components["schemas"]["ClosedJsonValue-Output"];
            financing: components["schemas"]["ClosedJsonValue-Output"];
            monthly_resources: components["schemas"]["ClosedJsonValue-Output"];
            rent: components["schemas"]["ClosedJsonValue-Output"];
            shared: components["schemas"]["ClosedJsonValue-Output"];
        };
        /**
         * ComparisonLedgerRowV1
         * @description One neutral common ledger row for the month 0..60 comparison timeline.
         */
        ComparisonLedgerRowV1: {
            /** Cash */
            cash: string;
            /** Consortium Credit Obligation Balance */
            consortium_credit_obligation_balance: string;
            /** Consortium Credit Right Balance */
            consortium_credit_right_balance: string;
            /** Cumulative Housing Cost */
            cumulative_housing_cost: string;
            /** Financing Principal Balance */
            financing_principal_balance: string;
            /** Home Equity */
            home_equity: string;
            /** Liquid Financial Assets */
            liquid_financial_assets: string;
            /** Liquidity */
            liquidity: string;
            /** Month */
            month: number;
            /** Net Worth */
            net_worth: string;
            /** Nonrecoverable Housing Cost */
            nonrecoverable_housing_cost: string;
            /** Property Value */
            property_value: string;
            /** Recoverable Transfer */
            recoverable_transfer: string;
            /** Total Liabilities */
            total_liabilities: string;
        };
        /** ComparisonLedgerV1 */
        ComparisonLedgerV1: {
            cash: components["schemas"]["MoneyOutput"];
            consortium_credit_obligation_balance: components["schemas"]["MoneyOutput"];
            consortium_credit_right_balance: components["schemas"]["MoneyOutput"];
            cumulative_housing_cost: components["schemas"]["MoneyOutput"];
            financing_principal_balance: components["schemas"]["MoneyOutput"];
            home_equity: components["schemas"]["MoneyOutput"];
            liquid_financial_assets: components["schemas"]["MoneyOutput"];
            liquidity: components["schemas"]["MoneyOutput"];
            /** Month */
            month: number;
            net_worth: components["schemas"]["MoneyOutput"];
            nonrecoverable_housing_cost: components["schemas"]["MoneyOutput"];
            property_value: components["schemas"]["MoneyOutput"];
            recoverable_transfer: components["schemas"]["MoneyOutput"];
            total_liabilities: components["schemas"]["MoneyOutput"];
        };
        /** ComparisonMetricsV1 */
        ComparisonMetricsV1: {
            final_ledger_row: components["schemas"]["ComparisonLedgerV1"];
            maximum_monthly_housing_outflow: components["schemas"]["MoneyOutput"];
            /** Maximum Monthly Housing Outflow Months */
            maximum_monthly_housing_outflow_months: number[];
            minimum_liquidity: components["schemas"]["MoneyOutput"];
            /** Minimum Liquidity Months */
            minimum_liquidity_months: number[];
        };
        /** ComparisonSimulationResultV1 */
        ComparisonSimulationResultV1: {
            /** Alternatives */
            alternatives: (components["schemas"]["FailedAlternativeV1"] | components["schemas"]["CompleteAlternativeV1"])[];
            /**
             * Api Version
             * @constant
             */
            api_version: "v1";
            /** Calculated At */
            calculated_at: string;
            /** Children */
            children: components["schemas"]["ComparisonChildV1"][];
            /**
             * Contract Schema Version
             * @constant
             */
            contract_schema_version: "comparison-simulation-v2";
            /** Data Snapshot Id */
            data_snapshot_id: string;
            declared_inputs: components["schemas"]["ComparisonInputsV1-Output"];
            /**
             * Engine Version
             * @constant
             */
            engine_version: "comparison-monthly-resources-v2";
            /**
             * Kind
             * @constant
             */
            kind: "simulation_result";
            /** Limitations */
            limitations: string[];
            normalized_input: components["schemas"]["NormalizedComparisonV1"];
            /**
             * Objective
             * @constant
             */
            objective: "maximize_net_worth_at_month_60";
            /** Ranking Groups */
            ranking_groups: components["schemas"]["Strategy"][][];
            /**
             * Ruleset Version
             * @constant
             */
            ruleset_version: "comparison-ruleset-v2";
            /**
             * Status
             * @enum {string}
             */
            status: "compared" | "single_eligible" | "no_eligible";
            /**
             * Timezone
             * @constant
             */
            timezone: "America/Sao_Paulo";
        };
        /** ComparisonViolationV1 */
        ComparisonViolationV1: {
            actual: components["schemas"]["MoneyOutput"];
            /**
             * Constraint
             * @enum {string}
             */
            constraint: "cash_nonnegative" | "minimum_liquidity" | "maximum_monthly_housing_outflow";
            /** Month */
            month: number;
            threshold: components["schemas"]["MoneyOutput"];
        };
        /** CompleteAlternativeV1 */
        CompleteAlternativeV1: {
            /** Comparison Ledger */
            comparison_ledger: components["schemas"]["ComparisonLedgerV1"][];
            metrics: components["schemas"]["ComparisonMetricsV1"];
            /** Monthly Housing Outflows */
            monthly_housing_outflows: components["schemas"]["MoneyOutput"][];
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            status: "constraint_infeasible" | "eligible";
            strategy: components["schemas"]["Strategy"];
            /** Violations */
            violations: components["schemas"]["ComparisonViolationV1"][];
        };
        /**
         * ContractualScheduleRowV1
         * @description One v3 contractual schedule posting.
         */
        ContractualScheduleRowV1: {
            /** Amortization */
            amortization: string;
            /** Closing Principal Balance */
            closing_principal_balance: string;
            /** Fee */
            fee: string;
            /** Interest */
            interest: string;
            /** Month */
            month: number;
            /** Opening Principal Balance */
            opening_principal_balance: string;
            /** Payment */
            payment: string;
        };
        /** FailedAlternativeV1 */
        FailedAlternativeV1: {
            failure: components["schemas"]["ComparisonFailureV1"];
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            status: "domain_failure";
            strategy: components["schemas"]["Strategy"];
        };
        /** @enum {string} */
        FailureCategory: "invalid_input" | "unsupported_rate_convention" | "unsupported_rule" | "unsupported_contract_clause" | "infeasible_scenario" | "incompatible_contract_version";
        /**
         * FinancingCalculationRequestV1
         * @description Request for one non-persistent, explicitly v3 financing projection.
         */
        FinancingCalculationRequestV1: {
            financing: components["schemas"]["FinancingInputV1"];
            /**
             * Strategy
             * @enum {string}
             */
            strategy: "sac" | "price";
        };
        /**
         * FinancingInputV1
         * @description HTTP-admitted financing fields; financial semantics remain in the domain.
         */
        FinancingInputV1: {
            /** Cash Down Payment */
            cash_down_payment: string;
            /** Comparison Opening Cash */
            comparison_opening_cash: string;
            /** Extraordinary Amortization Amount */
            extraordinary_amortization_amount?: string | null;
            /** Fee Amount */
            fee_amount?: string | null;
            /** Fgts Amount */
            fgts_amount?: string | null;
            /**
             * Indexation
             * @default not_requested
             * @enum {string}
             */
            indexation: "not_requested" | "documented_zero" | "requested_nonzero";
            /** Insurance Amount */
            insurance_amount?: string | null;
            /** Principal */
            principal: string;
            /** Property Price */
            property_price: string;
            /** Rate Convention */
            rate_convention: string;
            /** Rate Value */
            rate_value: string;
            /** Subsidy Amount */
            subsidy_amount?: string | null;
            /** Tax Amount */
            tax_amount?: string | null;
            /** Term Months */
            term_months: number;
            /** Transaction Cost Amount */
            transaction_cost_amount?: string | null;
        };
        IndexLocator: string;
        MoneyOutput: string;
        /** NormalizedComparisonV1 */
        NormalizedComparisonV1: {
            /** Constraints */
            constraints: {
                [key: string]: components["schemas"]["MoneyOutput"];
            };
            /** Input Classification */
            input_classification: {
                [key: string]: components["schemas"]["ClosedJsonValue-Output"];
            };
            monthly_resources: components["schemas"]["NormalizedResourcesV1"];
            /** Rule Conventions */
            rule_conventions: {
                [key: string]: components["schemas"]["ClosedJsonValue-Output"];
            };
            /** Shared */
            shared: {
                [key: string]: components["schemas"]["ClosedJsonValue-Output"];
            };
        };
        /** NormalizedResourceMonthV1 */
        NormalizedResourceMonthV1: {
            available_resources: components["schemas"]["MoneyOutput"];
            external_expense_total: components["schemas"]["MoneyOutput"];
            /** External Expenses */
            external_expenses: components["schemas"]["ResourceComponentV1"][];
            /** Income Components */
            income_components: components["schemas"]["ResourceComponentV1"][];
            income_total: components["schemas"]["MoneyOutput"];
            /** Month */
            month: number;
        };
        /** NormalizedResourcesV1 */
        NormalizedResourcesV1: {
            /**
             * Expense Scope
             * @constant
             */
            expense_scope: "strategy_independent_excluding_strategy_flows_and_netted_deductions";
            /**
             * Income Basis
             * @constant
             */
            income_basis: "net_before_household_expenses";
            /** Months */
            months: components["schemas"]["NormalizedResourceMonthV1"][];
        };
        OperationId: string;
        /** ResourceComponentV1 */
        ResourceComponentV1: {
            amount: components["schemas"]["MoneyOutput"];
            /** Assumption Reference */
            assumption_reference: string | null;
            /**
             * Classification
             * @enum {string}
             */
            classification: "observed_data" | "projected_assumption";
            /** Component Id */
            component_id: string;
            /** Source As Of */
            source_as_of: string;
            /** Source Reference */
            source_reference: string;
        };
        /** SavedComparisonCreationV1 */
        SavedComparisonCreationV1: {
            comparison: components["schemas"]["ComparisonInputsV1-Input"];
            operation_id: components["schemas"]["OperationId"];
        };
        /** SavedComparisonListV1 */
        SavedComparisonListV1: {
            /**
             * Api Version
             * @constant
             */
            api_version: "v1";
            /** Items */
            items: components["schemas"]["SavedComparisonSummaryV1"][];
            /**
             * Kind
             * @constant
             */
            kind: "saved_comparison_list";
            /** Next Offset */
            next_offset: number | null;
        };
        /** SavedComparisonSummaryV1 */
        SavedComparisonSummaryV1: {
            /** Saved At */
            saved_at: string;
            /** Simulation Id */
            simulation_id: string;
        };
        /** SavedComparisonV1 */
        SavedComparisonV1: {
            /**
             * Api Version
             * @constant
             */
            api_version: "v1";
            /**
             * Kind
             * @constant
             */
            kind: "saved_comparison";
            result: components["schemas"]["ComparisonSimulationResultV1"];
            /** Saved At */
            saved_at: string;
            simulation_id: components["schemas"]["OperationId"];
        };
        /** @enum {string} */
        Strategy: "sac" | "price" | "rent" | "consortium";
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    list_saved_api_v1_comparison_saved_simulations_get: {
        parameters: {
            query?: {
                limit?: number;
                offset?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SavedComparisonListV1"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ComparisonApiErrorV1"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ComparisonApiErrorV1"];
                };
            };
            /** @description Gone */
            410: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ComparisonApiErrorV1"];
                };
            };
            /** @description Content Too Large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ComparisonApiErrorV1"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ComparisonApiErrorV1"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ComparisonApiErrorV1"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ComparisonApiErrorV1"];
                };
            };
        };
    };
    create_saved_api_v1_comparison_saved_simulations_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SavedComparisonCreationV1"];
            };
        };
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SavedComparisonV1"];
                };
            };
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SavedComparisonV1"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ComparisonApiErrorV1"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ComparisonApiErrorV1"];
                };
            };
            /** @description Gone */
            410: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ComparisonApiErrorV1"];
                };
            };
            /** @description Content Too Large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ComparisonApiErrorV1"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ComparisonApiErrorV1"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ComparisonApiErrorV1"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ComparisonApiErrorV1"];
                };
            };
        };
    };
    read_saved_api_v1_comparison_saved_simulations__simulation_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                simulation_id: components["schemas"]["IndexLocator"];
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SavedComparisonV1"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ComparisonApiErrorV1"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ComparisonApiErrorV1"];
                };
            };
            /** @description Gone */
            410: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ComparisonApiErrorV1"];
                };
            };
            /** @description Content Too Large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ComparisonApiErrorV1"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ComparisonApiErrorV1"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ComparisonApiErrorV1"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ComparisonApiErrorV1"];
                };
            };
        };
    };
    delete_saved_api_v1_comparison_saved_simulations__simulation_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                simulation_id: components["schemas"]["IndexLocator"];
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ComparisonApiErrorV1"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ComparisonApiErrorV1"];
                };
            };
            /** @description Gone */
            410: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ComparisonApiErrorV1"];
                };
            };
            /** @description Content Too Large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ComparisonApiErrorV1"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ComparisonApiErrorV1"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ComparisonApiErrorV1"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ComparisonApiErrorV1"];
                };
            };
        };
    };
    create_simulation_api_v1_comparison_simulations_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ComparisonCreationRequestV1"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ComparisonSimulationResultV1"];
                };
            };
            /** @description Content Too Large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ComparisonApiErrorV1"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ComparisonApiErrorV1"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ComparisonApiErrorV1"];
                };
            };
        };
    };
    calculate_financing_projection_api_v1_financing_calculations_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FinancingCalculationRequestV1"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CalculationProjectionV1"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorV1"];
                };
            };
            /** @description Content Too Large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorV1"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorV1"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorV1"];
                };
            };
        };
    };
}
