import type { ReactElement, ReactNode } from "react";
import { describe, expect, it } from "vitest";

import RootLayout from "./layout";

type BodyProps = {
  children: ReactNode;
  suppressHydrationWarning?: boolean;
};

type HtmlProps = {
  children: ReactElement<BodyProps>;
  suppressHydrationWarning?: boolean;
};

describe("RootLayout", () => {
  it("suppresses extension-caused hydration warnings on root elements", () => {
    const layout = RootLayout({ children: <main>Eval Lab</main> }) as ReactElement<HtmlProps>;
    const body = layout.props.children;

    expect(layout.type).toBe("html");
    expect(layout.props.suppressHydrationWarning).toBe(true);
    expect(body.type).toBe("body");
    expect(body.props.suppressHydrationWarning).toBe(true);
    expect(body.props.children).toEqual(<main>Eval Lab</main>);
  });
});
