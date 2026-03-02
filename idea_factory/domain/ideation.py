"""Domain data and policies for autonomous idea generation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IdeationDomainProfile:
    """Describe one domain focus for autonomous idea generation."""

    name: str
    audience: str
    recurring_value: str
    acquisition_channel: str
    constraints: str


IDEATION_DOMAIN_PROFILES: tuple[IdeationDomainProfile, ...] = (
    IdeationDomainProfile(
        name="E-commerce Operations",
        audience="SMB operators on Shopify, WooCommerce, and marketplaces",
        recurring_value="monitoring revenue leaks, ops bottlenecks, and merchandising routines",
        acquisition_channel="app stores, SEO, operator communities",
        constraints="Prefer narrow workflow tools with obvious ROI in under one week.",
    ),
    IdeationDomainProfile(
        name="Finance Ops",
        audience="finance leads, founders, and controllers at small teams",
        recurring_value="cash monitoring, compliance reminders, and recurring close workflows",
        acquisition_channel="SEO, finance newsletters, accountant communities",
        constraints="Avoid regulated core-banking functions and focus on workflow visibility.",
    ),
    IdeationDomainProfile(
        name="Sales Operations",
        audience="small B2B teams with self-serve or hybrid sales motions",
        recurring_value="pipeline hygiene, follow-up orchestration, and renewal visibility",
        acquisition_channel="CRM marketplaces, templates, SEO",
        constraints="Avoid products that require enterprise procurement to close.",
    ),
    IdeationDomainProfile(
        name="Marketing Analytics",
        audience="growth marketers, agencies, and solo operators",
        recurring_value="campaign reporting, anomaly alerts, and recurring optimization loops",
        acquisition_channel="SEO, content, ecosystem marketplaces",
        constraints="Prefer products that improve decisions weekly without custom setup.",
    ),
    IdeationDomainProfile(
        name="Customer Support",
        audience="support managers and founders handling tickets directly",
        recurring_value="ticket triage, quality control, and deflection insights",
        acquisition_channel="helpdesk integrations, communities, SEO",
        constraints="Focus on measurable time saved or churn prevented.",
    ),
    IdeationDomainProfile(
        name="Developer Productivity",
        audience="engineering leads and small product teams",
        recurring_value="incident hygiene, code review flow, and release reliability",
        acquisition_channel="GitHub marketplace, dev content, community forums",
        constraints="Avoid generic coding copilots and target one painful repeated workflow.",
    ),
    IdeationDomainProfile(
        name="Compliance and Audit",
        audience="operations owners in regulated or semi-regulated SMBs",
        recurring_value="evidence collection, renewal tracking, and audit readiness",
        acquisition_channel="SEO, niche newsletters, partner referrals",
        constraints="Stay away from replacing legal advice; sell tracking and documentation.",
    ),
    IdeationDomainProfile(
        name="Vertical SaaS for Local Businesses",
        audience="clinics, studios, trades, and local service businesses",
        recurring_value="scheduling gaps, retention, and revenue leakage prevention",
        acquisition_channel="local SEO, niche directories, vendor communities",
        constraints="Target workflows that can be sold self-serve without onsite onboarding.",
    ),
    IdeationDomainProfile(
        name="HR and Recruiting Ops",
        audience="small teams hiring without a full HR department",
        recurring_value="candidate coordination, onboarding checklists, and policy reminders",
        acquisition_channel="HR communities, templates, SEO",
        constraints="Do not depend on heavy enterprise HRIS integrations to provide value.",
    ),
    IdeationDomainProfile(
        name="Data and Reporting",
        audience="operators living in spreadsheets and exports",
        recurring_value="scheduled reporting, exception alerts, and recurring reconciliations",
        acquisition_channel="SEO, spreadsheet templates, communities",
        constraints="Start with one repeated report or exception workflow, not a BI platform.",
    ),
)


IDEATION_CREATIVE_ANGLES: tuple[str, ...] = (
    "Find an unsexy, boring workflow that still creates obvious recurring value.",
    "Favor fast time-to-value and low support burden over ambitious scope.",
    "Bias toward data visibility, anomaly detection, and automated summaries.",
    "Prefer integrations with ecosystems that already have marketplace traffic.",
    "Look for revenue leak prevention, not just convenience.",
    "Focus on weekly operator rituals that teams already repeat manually.",
)


def clamp_idea_generation_count(requested_count: int) -> int:
    """Clamp autonomous generation requests into the supported range.

    Args:
        requested_count: Desired number of ideas.

    Returns:
        A safe count in the inclusive range 1..100.
    """

    return max(1, min(100, requested_count))
