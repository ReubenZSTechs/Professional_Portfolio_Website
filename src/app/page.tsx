import { Fragment } from "react";
import { sectionRegistry } from "@/components/sections/registry";
import { getHome } from "@/lib/content";

/** The homepage is assembled from content/home.yaml: edit that file to reorder or hide sections. */
export default function HomePage() {
  const { sections } = getHome();
  return (
    <>
      {sections
        .filter((s) => s.enabled)
        .map((section) => {
          const Component = sectionRegistry[section.id];
          return (
            <Fragment key={section.id}>
              <Component section={section} anchor={section.anchor ?? section.id} />
            </Fragment>
          );
        })}
    </>
  );
}
