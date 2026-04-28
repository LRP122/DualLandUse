# Agripholtaics Project

## Motivation

Agripholtaics is the process of combining agriculture and photovoltaics. This has a number of advantages.

![Agrivoltaics 101](References/images/Agrivoltaics101.png)

- Energy production due to solar panels
- Agricultural production
- Increased land use
- Less irrigation due to less evaporation
- Protection from extreme heat
- Possible IOT stations to monitor weather, soil, crop quality
- Possible protection from hail

## Project Idea
To find the agripholtaic potential for regions in Austria, different datasets will be gathered and combined into a scoring model:

- [x] Solar irradiance
- [x] Agricultural land use
- [ ] Weather Data on rain, heat, hail
- [ ] Prediction on weather in the future

These datasets will be overlaid on an interactive map. A user can select a region and receive an **agripholtaic value score** — a combined metric reflecting how beneficial agrivoltaics would be in that area (e.g. high solar yield + high heat stress on crops + hail risk = high value for installing panels).

It will also be necessary to research what crops are common in Austria and how much they benefit from agrivoltaic setups (shade tolerance, heat/hail protection, water retention), in order to weight the score correctly.

## First steps

![PhotovoltaicPowerPotentialAustria](References/images/Austria_PVOUT_mid-size-map_156x122mm-300dpi_v20191205.png)
- Collect Data on Agraratlas
- Collect Data on Solar Irradiance
- Analyze top agrar products for austria and their research with agripholtaics