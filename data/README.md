# Data

## Source

Zheng, Y., Wang, J., Zhang, Y., Mou, N., & Liu, Y. (2025). *A dataset of tourist mobility networks across China derived from online travel blogs*. Figshare. <https://doi.org/10.6084/m9.figshare.30184726.v1>

The dataset is licensed under the [Creative Commons Attribution 4.0 International License](https://creativecommons.org/licenses/by/4.0/). It may be shared and adapted with appropriate attribution.

## Files used

Run `python src/download_data.py` to obtain eight seasonal files:

- `Edges_Travels_in_{Season}.csv`: `Source`, `Target`, and `Weight`
- `Nodes_Travels_in_{Season}.csv`: attraction ID, Chinese and English names, city, and GCJ-02 coordinates

The project uses Spring, Summer, Autumn, and Winter. The four edge tables are combined and grouped by source-target pair to reconstruct the full observed network.

## Why raw data is excluded

The raw CSV files are downloaded from Figshare at analysis time and are ignored by Git. This keeps the repository small, avoids unnecessary redistribution, and makes the source and version explicit. Generated summary tables are stored in `results/`.

## Known limitations

- The records come from publicly posted Qunar travel blogs, not a representative survey of all tourists.
- Popular destinations and travelers who share trips online are likely overrepresented.
- The source period is approximately 2011-2021, so the results do not describe current absolute visitor volumes.
- Locations use GCJ-02 coordinates. They should not be combined directly with WGS-84 layers without an appropriate, lawful transformation.
- Edge weights count recorded consecutive attraction visits. They are not official passenger counts.
