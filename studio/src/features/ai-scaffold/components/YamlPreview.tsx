interface Props {
  yaml: string;
}

export function YamlPreview({ yaml }: Props) {
  return (
    <pre className="bg-gray-800 text-green-300 p-4 whitespace-pre-wrap">
      {yaml}
    </pre>
  );
}
