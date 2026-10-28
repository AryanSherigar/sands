interface CodeLine {
  line: string;
  indent?: string;
  key: string;
  val: string;
  isDanger?: boolean;
}

export interface WorkbenchCodeBlockProps {
  lines: CodeLine[];
}
