import { redirect } from "next/navigation";

/* Route historique conservée : l'explorateur vit désormais sur /decisions. */
export default function JurisprudencePage() {
  redirect("/decisions");
}
