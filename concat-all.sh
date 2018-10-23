for i in data/*.yaml; do cat "$i"; echo '\n---'; done > combined.yaml
sed -i '' -e '$ d' combined.yaml