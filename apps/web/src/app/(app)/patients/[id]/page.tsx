import { PatientDetail } from "@/components/patients/patient-detail";

// Static title on purpose: patient identity never goes into the tab title.
export const metadata = { title: "Detail pasien" };

export default async function PatientDetailPage(props: PageProps<"/patients/[id]">) {
  const { id } = await props.params;
  return <PatientDetail id={id} />;
}
