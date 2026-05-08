export const SIGNAL_TYPE_LABELS: Record<string, string> = {
  sloopmelding: "Sloopmelding ingediend",
  aangevraagde_sloopvergunning: "Sloopvergunning aangevraagd",
  verleende_sloopvergunning: "Sloopvergunning verleend",
  sloopvergunning_verleend: "Sloopvergunning verleend (BAG)",
  pand_buiten_gebruik: "Pand buiten gebruik (BAG)",
  concept_omgevingsvergunning: "Ontwerp omgevingsplan",
  mer_aanmelding: "MER-aanmelding",
  bestemmingswijziging: "Bestemmingswijziging",
  bestemmingswijziging_herziening: "Bestemmingswijziging herziening",
  ontwerp_plan: "Ontwerp omgevingsplan",
  ontwerp_omgevingsplan: "Ontwerp omgevingsplan",
  omgevingsplan_mutatie: "Omgevingsplan mutatie",
  eigendomsoverdracht: "Eigendomsoverdracht",
  rvb_aanbesteding: "RVB aanbesteding",
  koop_voornemen: "Voornemen tot verkoop",
};

export function signalTypeLabel(signalType: string): string {
  return SIGNAL_TYPE_LABELS[signalType] ?? signalType.replace(/_/g, " ");
}

export const EIGENAAR_TYPE_LABELS: Record<string, string> = {
  corporatie: "Woningcorporatie",
  corporatie_waarschijnlijk: "Waarschijnlijk corporatie",
  particulier_of_corporatie: "Particulier of corporatie",
  bedrijf: "Bedrijf",
  overheid: "Overheid",
  overheid_instelling: "Overheid / instelling",
  onbekend: "Onbekend",
};

export function eigenaarTypeLabel(type: string | null): string {
  if (!type) return "Onbekend";
  return EIGENAAR_TYPE_LABELS[type] ?? type;
}
