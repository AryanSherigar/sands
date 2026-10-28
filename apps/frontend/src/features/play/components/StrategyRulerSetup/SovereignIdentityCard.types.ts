export interface SovereignIdentityCardProps {
  name: string;
  epithet: string;
  portraitUrl?: string;
  dynastyName?: string;
  houseMotto?: string;
  onChangeName: (name: string) => void;
  onChangeEpithet: (epithet: string) => void;
}
