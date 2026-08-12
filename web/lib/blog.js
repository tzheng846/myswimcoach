// Swimnetics build log — the founder's dev journal turned into thematic posts.
// Plain data, no CMS. Posts are ordered oldest → newest; the index renders newest-first.
// Body blocks: { h } = section heading, { p } = paragraph.

export const posts = [
  {
    slug: "cutting-the-cord",
    kicker: "Hardware",
    title: "Cutting the cord: making the device stand on its own",
    excerpt:
      "The first real version of Swimnetics needed a laptop plugged into it at the edge of the pool. Getting rid of that meant going battery-powered — and learning the hard way which batteries are safe to hand a coach.",
    body: [
      {
        p: "For a long stretch, every test session came with a small knot of anxiety: my laptop, tethered to the device, sitting a few feet from a pool full of water. One bad splash and the whole project takes a very expensive detour. I was tired of fearing for its life. The device needed to stand on its own — and that meant a battery.",
      },
      {
        p: "My first instinct was a LiPo pack. Then I picked up a SparkFun board with a battery port, saw a 7,000 mAh hobby pack, and grabbed it without reading the label. It was 7.2 volts, and I found that out by burning my thumb on it. Lesson one: a battery I wouldn't trust in my own hands is not a battery I'm going to hand a coach. Hobby cells were out.",
      },
      { h: "The charger that kept falling asleep" },
      {
        p: "So I tried a normal portable phone charger instead. It worked for about 30 seconds, then shut off. Every time. It turns out many power banks have a feature where, if they don't sense a minimum current draw, they assume nothing's plugged in and go to sleep to save power — and the device's draw sat just below that threshold. After some digging I learned INIU chargers don't do this, spent $25 to confirm it, and finally had a power source that stayed awake.",
      },
      { h: "A box that fits the battery" },
      {
        p: "Of course, the battery pack was big, so the enclosure needed a redesign. After a lot of iterations I settled on separate compartments — one for the battery, one for the rest of the electronics — which kept the wiring sane and the heat away from things that don't like heat. I also added a status LED so there's a simple visual signal of what the device is doing.",
      },
      {
        p: "The payoff showed up the very next time I tested with the club swim group: I could leave my laptop back in the dry zone, well away from the splashes, and just let the device do its thing. That alone made the whole detour worth it.",
      },
    ],
  },
  {
    slug: "laughed-off-the-deck",
    kicker: "Field testing",
    title: "Laughed off the deck — and why it was the best thing that happened",
    excerpt:
      "I landed a demo at a real swim program in four days, scrambled to get ready, and watched almost everything that could break, break. It was humbling. It was also the clearest feedback I've ever gotten.",
    body: [
      {
        p: "Before the demo, two small hardware changes made a big difference. I moved the sensor from a vertical orientation to a horizontal one — it's far more stable and much easier to design around. And I finally added a string guide, after watching the tether jump off the sensor wheel over and over. I genuinely can't believe it took me that long to think of it.",
      },
      {
        p: "Then I called Sean from ASP, and he agreed to host a demo in four days. I scrambled to optimize everything I could and built a backup unit, because I had a feeling I'd need it.",
      },
      { h: "Building software from a kitchen table" },
      {
        p: "Part of that scramble happened away from my equipment. With no hardware to tinker with, I built out the software side instead: a React Native app for recording, Supabase for storing data, and a Railway-hosted API for processing. Building for iOS without a Mac is its own kind of pain — I couldn't simulate locally, so every build went to the cloud at roughly two dollars a pop. By the time things worked I was on my twenty-fifth build. None of it is wildly expensive, but none of it is free either.",
      },
      { h: "The demo" },
      {
        p: "Then I demoed at ASP, met some genuinely great people, and learned an enormous amount — mostly because so much went wrong. The sensor wheel had too much friction. A misprinted box started tearing apart. The line was too short and snapped once. Diving-block compatibility turned out to be a real question I hadn't thought through. And the part that still stings: I pulled out a fishing reel to retract the tether, got a good laugh from the room, and then the reel flew out of my hands and landed in a way that made the line saw straight through the plastic guide instead of riding gently along it.",
      },
      {
        p: "The big takeaway was unambiguous: a proper retraction mechanism wasn't a nice-to-have anymore. It was a requirement. You don't forget a lesson the room laughs you through.",
      },
    ],
  },
  {
    slug: "the-string-that-wouldnt-come-back",
    kicker: "Mechatronics",
    title: "The string that wouldn't come back",
    excerpt:
      "After the fishing-reel disaster, I needed a real way to retract 26 yards of tether. I wanted an elegant mechanical solution. I ended up learning to solder, frying my assumptions, and being saved by a one-dollar bearing.",
    body: [
      {
        p: "I'll be honest: I didn't want to deal with motors. Motors mean power systems and a hundred small, critical details I knew I'd miss and then suffer for. There had to be an elegant, mechanical-only answer.",
      },
      { h: "Chasing a spring" },
      {
        p: "Research pointed me at the obvious cousins — tape measures and retractable dog leashes use the same retracting trick. But spooling 26 yards of tether inside my size constraints is a different problem entirely. I bought a spiral spring and hoped. Then I learned spiral springs aren't constant-force: the swimmer would feel a hard pull at the start that drops off dramatically. Constant-force springs exist, but they're expensive and would need a gear ratio I wasn't confident I could design. After enough YouTube videos on retractable string pots, I admitted the purely mechanical path was beyond me — and, conveniently, talked myself into believing a motor is actually better for the user anyway.",
      },
      { h: "Learning electronics the slow way" },
      {
        p: "If only a motor were as simple as an LED. Power management was the first wall: how do you deliver the right voltage to both the ESP32 and the motor without frying either one? I bought a motor driver and a USB-C breakout, wired everything together with jumper wires, and the motor didn't spin. My housemate took one look and told me my wiring was a mess and I should solder.",
      },
      {
        p: "Soldering, it turns out, should not have been that hard — until I realized I'd been soldering components straight to wires to components like a lunatic, instead of using a protoboard. And it shouldn't have been that hard even then, until I admitted I should have drawn a schematic first. Once I did, the soldering went smoothly, and the motor finally spun. Somewhere in there I started thinking maybe I should learn proper PCB design and save myself the grief.",
      },
      { h: "The bearing that saved everything" },
      {
        p: "Then a new problem appeared: when the swimmer pulls the tether out, they back-drive the motor. With a high-rpm motor behind a 250:1 gearbox, that back-driving generates a serious current spike — the kind that makes you picture smoke. The fix was a one-way bearing. Spin it one direction and it free-wheels, so the swimmer pulls the line out with almost no resistance. Spin it the other and it locks, transmitting torque to spool the line back in. One inexpensive part erased the entire problem. I felt like a genius for about a day.",
      },
      {
        p: "The rest was tolerances — endless print-and-test cycles, and a sad pile of wasted filament. The breakthrough there came from someone else's design: if I print the string guide as a separate piece and attach it afterward, I can print the main body upside-down and skip a mountain of support material. I worried the join wouldn't be strong enough until I realized a heat-press makes it solid. That one change saved a huge amount of time and plastic.",
      },
    ],
  },
  {
    slug: "teaching-the-software-to-see-a-stroke",
    kicker: "Signal processing",
    title: "Teaching the software to see a stroke",
    excerpt:
      "Breaststroke was easy to break into clean cycles. Every other stroke fought me. The thing that finally worked also handed me something I wasn't even looking for.",
    body: [
      {
        p: "Segmenting a swim into individual stroke cycles sounds simple until you try it on more than one stroke. Breaststroke has an obvious glide where the velocity nearly drops to zero — easy boundaries. Freestyle and the others have continuous, overlapping propulsion and no dead spot to anchor on. Nothing I reached for worked.",
      },
      {
        p: "FFTs and spectral analysis let me down. I started wondering if it was time for machine learning — which would mean hand-labeling a pile of data, something I really didn't want to do.",
      },
      { h: "An elegant idea that didn't generalize" },
      {
        p: "Then my mentor pointed me at the matrix profile, a modern approach to time-series data mining. At its core it just computes Euclidean distance between subsequences, over and over — beautifully simple. I was hopeful. But it didn't generalize: the motifs locked onto a couple of cycles and refused to recognize the rest, and adding more motifs didn't rescue it. That was a genuinely disappointing week.",
      },
      { h: "Wavelets — and an accident" },
      {
        p: "So I tried wavelet analysis, and it worked. It surfaces bands of concentrated frequency — exactly the structure I needed — and, to my relief, it generalized across the other strokes too. Then I noticed it was finding multiple frequency bands at once. I assumed that was an artifact, looked closer, and realized it was separating the kick from the pull as distinct rhythms in the same swim. I wasn't looking for that. It might end up being one of the most useful things the device sees.",
      },
      {
        p: "A fair caveat: outside breaststroke, this segmentation is still early and experimental, and the app says so plainly rather than pretending otherwise. But the direction is right, and that's the part that had been missing.",
      },
    ],
  },
  {
    slug: "where-swimnetics-is-now",
    kicker: "Where we are & what's next",
    title: "Where Swimnetics is now — and what's coming",
    excerpt:
      "A quick honest snapshot: what's actually built today, the feedback that's shaping the next move, and an idea for the future I'm a little too excited about.",
    body: [
      {
        p: "Here's where things stand. The software backbone is real and running: an iOS app for recording, Supabase storing the data, a Railway-hosted API doing the signal processing, and a website now live at swimnetics.com. None of it is glamorous, but it's the plumbing that turns a wheel on a string into something a coach can actually use.",
      },
      { h: "The feedback that's steering the next step" },
      {
        p: "A former competitive swimmer who's now a data scientist took a look and gave me sharp, useful feedback. The clearest piece: I need a video overlay — the velocity data lined up against footage of the actual swim. So I'm starting with the simplest possible version, recording with a phone, and I'll judge from there whether it's worth the headache of an underwater camera.",
      },
      {
        p: "I'll be candid about a tension there. My north star is making the coach's experience effortless, and phone recording works against that, because someone has to hold the phone. It's a deliberate trade to learn fast before investing in something more involved.",
      },
      { h: "The idea I keep coming back to" },
      {
        p: "Which leads to the version I'm genuinely excited about: a camera mounted on a carriage at the pool's edge that rolls along the deck, motorized and paired with computer vision, automatically tracking the swimmer down the lane. No one holding anything. It's well off in the future — but it's the kind of idea that keeps me building.",
      },
    ],
  },
];

export function getPost(slug) {
  return posts.find((p) => p.slug === slug);
}

export const postsNewestFirst = [...posts].reverse();
