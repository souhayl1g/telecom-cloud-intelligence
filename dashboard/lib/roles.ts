// Single source of truth for the 3-persona RBAC the dashboard is built around.
// Used by BOTH the Edge middleware (route gating) and the Sidebar (nav filtering)
// so navigation and access never drift apart.
//
// SECURITY NOTE: the middleware that consumes this is a UX guard only — it reads
// the role from the JWT payload without verifying the signature. The REAL security
// boundary is the api-gateway `require_role` dependency, which verifies the token on
// every data call. A forged role cookie only reveals an empty page shell; every API
// request behind it returns 403.

export type Role = "engineer" | "data_scientist" | "admin";
export const ALL_ROLES: Role[] = ["engineer", "data_scientist", "admin"];

export const ROLE_LABEL: Record<Role, string> = {
    engineer: "Telecom Engineer",
    data_scientist: "Data Scientist",
    admin: "Administrator",
};

// path prefix -> roles allowed. `admin` is implicitly allowed everywhere (super-role),
// so it never needs listing. Longest-prefix match wins.
type Rule = { prefix: string; roles: Role[] };
const ACCESS: Rule[] = [
    // Admin-only
    { prefix: "/admin", roles: [] }, // admin super-role only

    // Data Scientist surfaces (model internals, data, drift, notebooks)
    { prefix: "/model-evaluation", roles: ["data_scientist"] },
    { prefix: "/data-warehouse", roles: ["data_scientist"] },
    { prefix: "/data-explorer", roles: ["data_scientist"] },
    { prefix: "/data-drift", roles: ["data_scientist"] },
    { prefix: "/notebook-lab", roles: ["data_scientist"] },
    { prefix: "/intelligence", roles: ["data_scientist"] },
    { prefix: "/minio", roles: ["data_scientist"] },
    { prefix: "/mlflow", roles: ["data_scientist"] },

    // Telecom Engineer surfaces (results, ops, automation, observability)
    { prefix: "/cem-scores", roles: ["engineer"] },
    { prefix: "/vae-anomalies", roles: ["engineer"] },
    { prefix: "/rat-underservice", roles: ["engineer"] },
    { prefix: "/oss-cells", roles: ["engineer"] },
    { prefix: "/bss-subscribers", roles: ["engineer"] },
    { prefix: "/tickets", roles: ["engineer"] },
    { prefix: "/notifications", roles: ["engineer"] },
    { prefix: "/interventions", roles: ["engineer"] },
    { prefix: "/reports", roles: ["engineer"] },
    { prefix: "/capacity", roles: ["engineer"] },
    { prefix: "/predictive", roles: ["engineer"] },
    { prefix: "/ops-metrics", roles: ["engineer"] },
    { prefix: "/pipeline-runs", roles: ["engineer"] },
    { prefix: "/metrics", roles: ["engineer"] },
    { prefix: "/traces", roles: ["engineer"] },

    // Shared across Engineer + Data Scientist (convergence + the L4 hero)
    { prefix: "/overview", roles: ["engineer", "data_scientist"] },
    { prefix: "/l4-agent", roles: ["engineer", "data_scientist"] },
    { prefix: "/data-lake", roles: ["engineer", "data_scientist"] },
    { prefix: "/granger-causality", roles: ["engineer", "data_scientist"] },
    { prefix: "/correlations", roles: ["engineer", "data_scientist"] },
];

/** Roles allowed for a path (admin always allowed). Unlisted paths => all roles. */
export function rolesForPath(path: string): Role[] {
    const match = ACCESS
        .filter((r) => path === r.prefix || path.startsWith(r.prefix + "/"))
        .sort((a, b) => b.prefix.length - a.prefix.length)[0];
    if (!match) return ALL_ROLES; // not a gated page (e.g. settings, generic)
    return Array.from(new Set<Role>([...match.roles, "admin"]));
}

export function canAccess(path: string, role: Role | undefined): boolean {
    if (!role) return false;
    return rolesForPath(path).includes(role);
}

/** Where each persona lands after login. */
export function defaultLanding(role: Role | undefined): string {
    if (role === "admin") return "/admin";
    if (role === "data_scientist") return "/model-evaluation";
    return "/overview"; // engineer (and fallback)
}
