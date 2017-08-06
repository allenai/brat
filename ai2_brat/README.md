# Workflow

## Derandomize

Take the documents which have had random prefixes attached and rename them to
just their normal identifiers. This is done annotator directory by annotator
directory.

``` shell
usage: copy_randomize_files.py [-h] --from-dir FROM_DIR --to-dir TO_DIR
                               [--derandomize] [--abstract-only] [--override]

# In the root of the brat repo
python copy_randomize_files.py --from-dir data/craft/kevin --to-dir derandomized/kevin
```

## Automatic fixup

Perform some automated fixups on individual directories of data.

``` shell
usage: fixup_annotations.py [-h] [--outputPath OUTPUTPATH] paths [paths ...]

# In the the brat repo
python3 ai2_brat/fixup_annotations.py --outputPath fixed derandomized/kevin
```

## Measure Agreement

It might be useful to measure the inter-annotator agreement.

``` shell
usage: measure_agreement.py [-h] [--relaxed] [--considerDiscontinuous]
                            [--entityTypes [ENTITYTYPES [ENTITYTYPES ...]]]
                            [--relationTypes [RELATIONTYPES [RELATIONTYPES ...]]]
                            paths [paths ...]

# In the the brat repo
python3 ai2_brat/measure_agreement.py data/craft/{kevin, sandy}
```

There are a number of options to choose among. `--relaxed` is perhaps the most
common to use.

## Automatic merge

Merge multiple annotations to be adjudicated.

Note: It is important that the directories to `merge_annotations.py merge` be
specified in the same order each time, as this influences the IDs that are used
in the output.

``` shell
usage: merge_annotations.py merge [-h] [--verbose]
                                  correction_dir annotator_dirs
                                  [annotator_dirs ...]

# In the brat repo
python3 ai2_brat/merge_annotations.py merge intermediate/ fixed/kevin fixed/sandy

# Now we need to attach the entity linking annotations
usage: merge_annotations.py merge_linking [-h] [--verbose]
                                          correction_dir base_dir linking_dir
                                          
python3 ai2_brat/merge_annotations.py merge_linking corrections intermediate path/to/linking_annotations

```

`corrections` should then be copied to the brat server and worked on by an
adjudicator. `visual_merge.conf` and `annotation_merge.conf` should be renamed
to `visual.conf` and `annotation.conf` and placed in the `corrections` directory
on the brat server.

After the adjudicator is done, we should check that there do not remain any
contested annotations.

``` shell
# In the brat repo
usage: merge_annotations.py verify [-h] [--verbose] correction_dir

python3 ai2_brat/merge_annotations.py verify corrections
```
