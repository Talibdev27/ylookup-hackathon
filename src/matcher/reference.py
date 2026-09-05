"""The reference lists a stage matches against.

Every stage receives one of these. It is the only thing a stage is told about the world
beyond its own row, which keeps the stage seam to two parameters.

Two adapters satisfy it, which is what makes the seam real rather than hypothetical:

    ReferenceLists.from_workbook(sheets)   the client's actual workbook
    ReferenceLists(legal_entities=[...])   an in-memory fake, three lines, for tests

Sheet names live in here and nowhere else. Before this module they were spread between
the loader and the stages, so `"Deal & Position Master List"` appeared in two packages
and a renamed sheet broke matching in a place with no mention of sheets at all.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ReferenceLists:
    """What the matcher matches against.

    Every list defaults to empty so a test builds only the part it cares about.
    """

    legal_entities: list[str] = field(default_factory=list)
    related_parties: list[str] = field(default_factory=list)
    investors: list[str] = field(default_factory=list)
    vendors: list[str] = field(default_factory=list)
    deal_names: list[str] = field(default_factory=list)
    project_codes: list[dict[str, str]] = field(default_factory=list)
    deals: list[dict[str, str]] = field(default_factory=list)

    #: The client's own code for the group these entities belong to, read from the
    #: `Legal Entity Domain` column the reference sheets all carry. Every one of the 297
    #: related parties in the sample workbook is `NIP`, which is what makes it useful: a
    #: counterparty the lists do not name, but whose name opens with this code, is still
    #: one of the group's own.
    domain_code: str = ""

    # The sheets a workbook must carry, and the column each list is read from.
    SHEETS = {
        "legal_entities": ("Legal Entity Master List", "Legal Entity"),
        "related_parties": ("Related Party Master", "Related Party"),
        "investors": ("Investor Master List", "Investor"),
        "vendors": ("Vendor Master List", "Vendor"),
        "deal_names": ("Deal & Position Master List", "Deal Name"),
    }

    @classmethod
    def from_workbook(cls, sheets: dict[str, list[dict[str, str]]]) -> ReferenceLists:
        """Build from a parsed workbook. The only place sheet and column names appear."""

        def names(key: str) -> list[str]:
            sheet, column = cls.SHEETS[key]
            return sorted({r[column] for r in sheets.get(sheet, []) if r.get(column)})

        domains = Counter(
            (row.get("Legal Entity Domain") or "").strip()
            for row in sheets.get("Related Party Master", [])
        )
        domains.pop("", None)

        return cls(
            domain_code=domains.most_common(1)[0][0] if domains else "",
            legal_entities=names("legal_entities"),
            related_parties=names("related_parties"),
            investors=names("investors"),
            vendors=names("vendors"),
            deal_names=names("deal_names"),
            project_codes=sheets.get("Project Code Report", []),
            deals=sheets.get("Deal & Position Master List", []),
        )

    def canonical_spelling(self, name: str) -> str:
        """The deal master's spelling of an entity the lists disagree about.

        38 entities appear on more than one sheet spelled differently -- `NI DRACONIS
        HOLDCO I SCSp` on the related party master is `NI Draconis HoldCo I SCSp` on the
        deal master, and `NI V Kalvik TopCo Limited.` loses its full stop. They are the
        same company, so which one gets written out is a choice, and the deal master is
        the register the journal entries load against.

        Only the spelling moves. Which list the counterparty was *found* on is a different
        fact, and `classification` depends on it, so the caller keeps its own source.
        """
        from src.matcher.counterparty import fold_legal_form

        target = fold_legal_form(name)
        if not target:
            return name
        for entry in self.deal_names:
            if fold_legal_form(entry) == target:
                return entry
        return name

    def counterparty_lists(self) -> list[tuple[str, list[str]]]:
        """The lists to search for a counterparty, in the order the Process sheet reviews
        them: related party, then legal entity, then investor, then vendor, then deal.

        The order is the point. A counterparty that is a related party is a related party,
        even when the same name also appears as a vendor -- and some counterparties are
        held per currency and exist only in the deal list, which is why deals are in here
        at all. This rule used to be written inline inside one stage, where the next stage
        needing it would have had to copy it.
        """
        return [
            ("Related Party Master", self.related_parties),
            ("Legal Entity Master List", self.legal_entities),
            ("Investor Master List", self.investors),
            ("Vendor Master List", self.vendors),
            ("Deal & Position Master List", self.deal_names),
        ]
