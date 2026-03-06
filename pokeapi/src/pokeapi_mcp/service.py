"""PokeAPIService — wraps the PokeAPI v2 into proto RPCs."""

from __future__ import annotations

from typing import Any

import httpx

from pokeapi_mcp.gen.pokeapi.v1 import pokeapi_pb2 as pb

_BASE_URL = "https://pokeapi.co/api/v2"


class PokeAPIService:
    """Implements PokeAPIService RPCs via the free PokeAPI v2."""

    def __init__(self):
        self._http = httpx.Client(timeout=30)

    def _get(self, path: str, params: dict | None = None) -> Any:
        resp = self._http.get(f"{_BASE_URL}{path}", params=params)
        resp.raise_for_status()
        return resp.json()

    def GetPokemon(self, request: Any, context: Any = None) -> pb.GetPokemonResponse:
        raw = self._get(f"/pokemon/{request.name_or_id}")

        types = []
        for t in raw.get("types", []):
            type_info = t.get("type", {})
            types.append(pb.PokemonType(
                name=type_info.get("name", ""),
                slot=t.get("slot", 0),
            ))

        stats = []
        for s in raw.get("stats", []):
            stat_info = s.get("stat", {})
            stats.append(pb.PokemonStat(
                name=stat_info.get("name", ""),
                base_stat=s.get("base_stat", 0),
                effort=s.get("effort", 0),
            ))

        abilities = []
        for a in raw.get("abilities", []):
            ability_info = a.get("ability", {})
            abilities.append(pb.PokemonAbility(
                name=ability_info.get("name", ""),
                is_hidden=a.get("is_hidden", False),
                slot=a.get("slot", 0),
            ))

        sprites_raw = raw.get("sprites", {})
        sprites = pb.PokemonSprites(
            front_default=sprites_raw.get("front_default", "") or "",
            front_shiny=sprites_raw.get("front_shiny", "") or "",
            back_default=sprites_raw.get("back_default", "") or "",
            back_shiny=sprites_raw.get("back_shiny", "") or "",
        )

        return pb.GetPokemonResponse(
            id=raw.get("id", 0),
            name=raw.get("name", ""),
            types=types,
            stats=stats,
            abilities=abilities,
            height=raw.get("height", 0),
            weight=raw.get("weight", 0),
            sprites=sprites,
            base_experience=raw.get("base_experience", 0) or 0,
            order=raw.get("order", 0),
        )

    def GetPokemonSpecies(self, request: Any, context: Any = None) -> pb.GetPokemonSpeciesResponse:
        raw = self._get(f"/pokemon-species/{request.name_or_id}")

        # Get English flavor text.
        flavor_text = ""
        for entry in raw.get("flavor_text_entries", []):
            lang = entry.get("language", {})
            if lang.get("name") == "en":
                flavor_text = entry.get("flavor_text", "")
                break

        # Get English genus.
        genus = ""
        for entry in raw.get("genera", []):
            lang = entry.get("language", {})
            if lang.get("name") == "en":
                genus = entry.get("genus", "")
                break

        generation = raw.get("generation", {})
        habitat = raw.get("habitat", {}) or {}
        evolution_chain = raw.get("evolution_chain", {}) or {}
        color = raw.get("color", {}) or {}
        shape = raw.get("shape", {}) or {}

        return pb.GetPokemonSpeciesResponse(
            id=raw.get("id", 0),
            name=raw.get("name", ""),
            flavor_text=flavor_text,
            genus=genus,
            generation=generation.get("name", ""),
            habitat=habitat.get("name", "") or "",
            is_legendary=raw.get("is_legendary", False),
            is_mythical=raw.get("is_mythical", False),
            evolution_chain_url=evolution_chain.get("url", ""),
            capture_rate=raw.get("capture_rate", 0),
            base_happiness=raw.get("base_happiness", 0) or 0,
            color=color.get("name", "") or "",
            shape=shape.get("name", "") or "",
        )

    def GetAbility(self, request: Any, context: Any = None) -> pb.GetAbilityResponse:
        raw = self._get(f"/ability/{request.name_or_id}")

        # Get English effect.
        effect = ""
        short_effect = ""
        for entry in raw.get("effect_entries", []):
            lang = entry.get("language", {})
            if lang.get("name") == "en":
                effect = entry.get("effect", "")
                short_effect = entry.get("short_effect", "")
                break

        pokemon = []
        for p in raw.get("pokemon", []):
            poke_info = p.get("pokemon", {})
            pokemon.append(pb.AbilityPokemon(
                name=poke_info.get("name", ""),
                is_hidden=p.get("is_hidden", False),
            ))

        return pb.GetAbilityResponse(
            id=raw.get("id", 0),
            name=raw.get("name", ""),
            effect=effect,
            short_effect=short_effect,
            pokemon=pokemon,
        )

    def GetMove(self, request: Any, context: Any = None) -> pb.GetMoveResponse:
        raw = self._get(f"/move/{request.name_or_id}")

        # Get English effect.
        effect = ""
        short_effect = ""
        for entry in raw.get("effect_entries", []):
            lang = entry.get("language", {})
            if lang.get("name") == "en":
                effect = entry.get("effect", "")
                short_effect = entry.get("short_effect", "")
                break

        type_info = raw.get("type", {})
        damage_class = raw.get("damage_class", {})

        return pb.GetMoveResponse(
            id=raw.get("id", 0),
            name=raw.get("name", ""),
            power=raw.get("power", 0) or 0,
            accuracy=raw.get("accuracy", 0) or 0,
            pp=raw.get("pp", 0) or 0,
            type=type_info.get("name", ""),
            damage_class=damage_class.get("name", "") or "",
            effect=effect,
            short_effect=short_effect,
            priority=raw.get("priority", 0),
        )

    def GetType(self, request: Any, context: Any = None) -> pb.GetTypeResponse:
        raw = self._get(f"/type/{request.name_or_id}")

        dr = raw.get("damage_relations", {})

        def extract_names(key: str) -> list[str]:
            return [item.get("name", "") for item in dr.get(key, [])]

        damage_relations = pb.DamageRelations(
            double_damage_to=extract_names("double_damage_to"),
            half_damage_to=extract_names("half_damage_to"),
            no_damage_to=extract_names("no_damage_to"),
            double_damage_from=extract_names("double_damage_from"),
            half_damage_from=extract_names("half_damage_from"),
            no_damage_from=extract_names("no_damage_from"),
        )

        pokemon_names = []
        for p in raw.get("pokemon", []):
            poke_info = p.get("pokemon", {})
            pokemon_names.append(poke_info.get("name", ""))

        move_names = [m.get("name", "") for m in raw.get("moves", [])]

        return pb.GetTypeResponse(
            id=raw.get("id", 0),
            name=raw.get("name", ""),
            damage_relations=damage_relations,
            pokemon=pokemon_names,
            moves=move_names,
        )

    def GetEvolutionChain(self, request: Any, context: Any = None) -> pb.GetEvolutionChainResponse:
        raw = self._get(f"/evolution-chain/{request.id}")

        def parse_chain(chain_data: dict) -> pb.EvolutionLink:
            species = chain_data.get("species", {})
            species_name = species.get("name", "")

            # Parse evolution details for the trigger/conditions.
            details_list = chain_data.get("evolution_details", [])
            trigger = ""
            min_level = 0
            item = ""
            if details_list:
                details = details_list[0]
                trigger_info = details.get("trigger", {})
                trigger = trigger_info.get("name", "")
                min_level = details.get("min_level", 0) or 0
                item_info = details.get("item", {}) or {}
                item = item_info.get("name", "") or ""

            evolves_to = []
            for evo in chain_data.get("evolves_to", []):
                evolves_to.append(parse_chain(evo))

            return pb.EvolutionLink(
                species_name=species_name,
                trigger=trigger,
                min_level=min_level,
                item=item,
                evolves_to=evolves_to,
            )

        chain_data = raw.get("chain", {})
        chain = parse_chain(chain_data)

        return pb.GetEvolutionChainResponse(
            id=raw.get("id", 0),
            chain=chain,
        )

    def GetGeneration(self, request: Any, context: Any = None) -> pb.GetGenerationResponse:
        raw = self._get(f"/generation/{request.name_or_id}")

        main_region = raw.get("main_region", {})
        pokemon_species = [s.get("name", "") for s in raw.get("pokemon_species", [])]
        moves = [m.get("name", "") for m in raw.get("moves", [])]
        types = [t.get("name", "") for t in raw.get("types", [])]

        return pb.GetGenerationResponse(
            id=raw.get("id", 0),
            name=raw.get("name", ""),
            main_region=main_region.get("name", ""),
            pokemon_species=pokemon_species,
            moves=moves,
            types=types,
        )

    def GetItem(self, request: Any, context: Any = None) -> pb.GetItemResponse:
        raw = self._get(f"/item/{request.name_or_id}")

        # Get English effect.
        effect = ""
        short_effect = ""
        for entry in raw.get("effect_entries", []):
            lang = entry.get("language", {})
            if lang.get("name") == "en":
                effect = entry.get("effect", "")
                short_effect = entry.get("short_effect", "")
                break

        category = raw.get("category", {})
        sprites = raw.get("sprites", {})

        return pb.GetItemResponse(
            id=raw.get("id", 0),
            name=raw.get("name", ""),
            effect=effect,
            short_effect=short_effect,
            category=category.get("name", ""),
            cost=raw.get("cost", 0),
            sprite=sprites.get("default", "") or "",
        )

    def GetNature(self, request: Any, context: Any = None) -> pb.GetNatureResponse:
        raw = self._get(f"/nature/{request.name_or_id}")

        increased_stat = raw.get("increased_stat", {}) or {}
        decreased_stat = raw.get("decreased_stat", {}) or {}

        return pb.GetNatureResponse(
            id=raw.get("id", 0),
            name=raw.get("name", ""),
            increased_stat=increased_stat.get("name", "") or "",
            decreased_stat=decreased_stat.get("name", "") or "",
        )

    def ListPokemon(self, request: Any, context: Any = None) -> pb.ListPokemonResponse:
        params = {
            "limit": request.limit or 20,
            "offset": request.offset or 0,
        }
        raw = self._get("/pokemon", params=params)

        results = []
        for r in raw.get("results", []):
            results.append(pb.NamedResource(
                name=r.get("name", ""),
                url=r.get("url", ""),
            ))

        return pb.ListPokemonResponse(
            count=raw.get("count", 0),
            next=raw.get("next", "") or "",
            previous=raw.get("previous", "") or "",
            results=results,
        )
