import { useEffect, useState } from "react";
import { MotionConfig } from "motion/react";
import { Nav } from "./components/landing/Nav";
import { Hero } from "./components/landing/Hero";
import { Challenge, Features, Product } from "./components/landing/Story";
import { Closing, Comparison, Delivered, Footer, ProductFrame, Sources, Team } from "./components/landing/Proof";
import { Problem } from "./components/landing/Intro";
import { Stack } from "./components/landing/Stack";
import { Workspace } from "./workspace/Workspace";
import { DemoRun } from "./workspace/connected/DemoRun";

// Hash routing keeps the build static: "#/app" is the guided demo run, "#/app/manual" the manual workspace,
// anything else the landing page.
function useRoute() {
  const read = () => {
    const hash = window.location.hash;
    return hash.startsWith("#/app/manual") ? "manual" : hash.startsWith("#/app") ? "app" : "landing";
  };
  const [route, setRoute] = useState(read);
  useEffect(() => {
    const onHash = () => setRoute(read());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  return route;
}

function Landing() {
  return (
    <>
      <Nav />
      <main>
        <Hero />
        <Challenge />
        <Problem />
        <Product />
        <Features />
        <ProductFrame />
        <Stack />
        <Delivered />
        <Comparison />
        <Team />
        <Sources />
        <Closing />
      </main>
      <Footer />
    </>
  );
}

export default function App() {
  const route = useRoute();
  useEffect(() => {
    if (route !== "landing") window.scrollTo(0, 0);
  }, [route]);
  return (
    <MotionConfig reducedMotion="user">
      {route === "app" ? <DemoRun /> : route === "manual" ? <Workspace /> : <Landing />}
    </MotionConfig>
  );
}
