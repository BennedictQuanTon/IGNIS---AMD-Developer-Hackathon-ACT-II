import { useEffect, useState } from "react";
import { MotionConfig } from "motion/react";
import { Nav } from "./components/landing/Nav";
import { Hero } from "./components/landing/Hero";
import { Challenge, Features, Product } from "./components/landing/Story";
import { Closing, Comparison, Delivered, Footer, ProductFrame, Sources, Team } from "./components/landing/Proof";
import { Figures, Statement, Strip } from "./components/landing/Intro";
import { Stack } from "./components/landing/Stack";
import { Workspace } from "./workspace/Workspace";

// Hash routing keeps the build static: "#/app" is the workspace, anything else the landing page.
function useRoute() {
  const read = () => (window.location.hash.startsWith("#/app") ? "app" : "landing");
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
        <Strip />
        <Statement />
        <Figures />
        <Challenge />
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
    if (route === "app") window.scrollTo(0, 0);
  }, [route]);
  return <MotionConfig reducedMotion="user">{route === "app" ? <Workspace /> : <Landing />}</MotionConfig>;
}
