import { redirect } from "next/navigation";

/* Route historique conservée : le simulateur vit désormais sur /simulateur. */
export default function BoussolePage() {
  redirect("/simulateur");
}
