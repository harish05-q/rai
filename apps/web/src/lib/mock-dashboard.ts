export const dashboardMetrics = [
  {
    label: "Revenue at Risk",
    value: "₹18.42L",
    note: "Mock value across failed and pending payment events."
  },
  {
    label: "Recovered Revenue",
    value: "₹7.31L",
    note: "Mock recovered amount for Sprint 1 dashboard validation."
  },
  {
    label: "Recovery Rate",
    value: "39.7%",
    note: "Mock ratio of recovered revenue to at-risk revenue."
  },
  {
    label: "Active Recovery Cases",
    value: "427",
    note: "Mock queue size for recovery operations readiness."
  }
];

export const dashboardActivity = [
  {
    title: "Payment analyzed",
    description: "A failed card payment was classified for recoverability using mock Sprint 1 data.",
    time: "2m ago",
    kind: "analysis" as const
  },
  {
    title: "Recovery strategy selected",
    description: "A bounded retry path was selected as a placeholder event with no execution authority.",
    time: "12m ago",
    kind: "strategy" as const
  },
  {
    title: "Payment recovered",
    description: "A mock payment moved into recovered status for dashboard layout testing.",
    time: "24m ago",
    kind: "recovered" as const
  }
];
