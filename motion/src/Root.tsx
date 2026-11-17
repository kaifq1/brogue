import { Composition } from "remotion";
import { Film } from "./Film";

// One continuous camera move over one sheet, 16:9, for the README, the site and social posts.
export const RemotionRoot: React.FC = () => (
  <>
    <Composition id="Brogue" component={Film} durationInFrames={31 * 30} fps={30} width={1920} height={1080} />
  </>
);
