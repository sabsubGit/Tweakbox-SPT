#!/usr/bin/env bash
# Builds both projects and assembles a drag-and-drop release zip in dist/.
#   ./package.sh                       uses `dotnet` from PATH
#   DOTNET=/path/to/dotnet ./package.sh
# The zip has BepInEx/ (client plugin) and SPT/ (server mod) at its top level.
# Note: the client project compiles against game assemblies that are not in this
# repo - point the Assembly-CSharp HintPath in Client/TweakboxClient.csproj at
# your own EscapeFromTarkov_Data/Managed before building.
set -euo pipefail
cd "$(dirname "$0")"
DOTNET="${DOTNET:-dotnet}"

VERSION=$(grep -oP 'Version Version \{.*new\("\K[0-9.]+' TweakboxMetadata.cs)
[ -n "$VERSION" ] || { echo "could not read the version from TweakboxMetadata.cs" >&2; exit 1; }

"$DOTNET" build Tweakbox.csproj -c Release --nologo -v q
"$DOTNET" build Client/TweakboxClient.csproj -c Release --nologo -v q

STAGE="dist/stage"
rm -rf dist && mkdir -p "$STAGE/BepInEx/plugins/TweakboxClient" "$STAGE/SPT/user/mods/Tweakbox"
# Only our own DLL: the client build output also holds copied game reference assemblies
# (hollowed.dll and friends) which must never be redistributed.
cp Client/bin/Release/netstandard2.1/TweakboxClient.dll "$STAGE/BepInEx/plugins/TweakboxClient/"
cp bin/Release/net10.0/Tweakbox.dll config.json         "$STAGE/SPT/user/mods/Tweakbox/"
# Custom item models/textures (the IDEA Iskub). The server hands these to every connecting client.
[ -f bundles.json ] && [ -d bundles ] || { echo "bundles/ or bundles.json missing - run tools/rebuild_iskub.sh" >&2; exit 1; }
cp -r bundles bundles.json                              "$STAGE/SPT/user/mods/Tweakbox/"
# Safety net: the release must never contain the Testing-build debug helpers (F12 mail buttons / server route).
for dll in "$STAGE/BepInEx/plugins/TweakboxClient/TweakboxClient.dll" "$STAGE/SPT/user/mods/Tweakbox/Tweakbox.dll"; do
    if strings -e l "$dll" | grep -qE 'tweakbox/debug|Debug \(testing build only\)'; then
        echo "refusing to package: $dll contains Testing-build debug code" >&2
        exit 1
    fi
done
cp LICENSE "$STAGE/"
sed "s/@VERSION@/$VERSION/" release/README.txt > "$STAGE/README.txt"

ZIP="Tweakbox-$VERSION.zip"
( cd "$STAGE" && zip -qr "../$ZIP" README.txt LICENSE BepInEx SPT )
rm -rf "$STAGE"
echo "built dist/$ZIP"
