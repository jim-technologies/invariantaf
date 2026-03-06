"""Unit tests — every PokeAPIService RPC method, mocked HTTP."""

import pytest
from unittest.mock import MagicMock

from pokeapi_mcp.gen.pokeapi.v1 import pokeapi_pb2 as pb
from tests.conftest import (
    FAKE_ABILITY,
    FAKE_EVOLUTION_CHAIN,
    FAKE_GENERATION,
    FAKE_ITEM,
    FAKE_LIST_POKEMON,
    FAKE_MOVE,
    FAKE_NATURE,
    FAKE_POKEMON,
    FAKE_POKEMON_SPECIES,
    FAKE_TYPE,
)


class TestGetPokemon:
    def test_basic_fields(self, service):
        resp = service.GetPokemon(pb.GetPokemonRequest(name_or_id="pikachu"))
        assert resp.id == 25
        assert resp.name == "pikachu"
        assert resp.height == 4
        assert resp.weight == 60
        assert resp.base_experience == 112
        assert resp.order == 35

    def test_types(self, service):
        resp = service.GetPokemon(pb.GetPokemonRequest(name_or_id="pikachu"))
        assert len(resp.types) == 1
        assert resp.types[0].name == "electric"
        assert resp.types[0].slot == 1

    def test_stats(self, service):
        resp = service.GetPokemon(pb.GetPokemonRequest(name_or_id="pikachu"))
        assert len(resp.stats) == 6
        hp = [s for s in resp.stats if s.name == "hp"][0]
        assert hp.base_stat == 35
        speed = [s for s in resp.stats if s.name == "speed"][0]
        assert speed.base_stat == 90
        assert speed.effort == 2

    def test_abilities(self, service):
        resp = service.GetPokemon(pb.GetPokemonRequest(name_or_id="pikachu"))
        assert len(resp.abilities) == 2
        static = [a for a in resp.abilities if a.name == "static"][0]
        assert static.is_hidden is False
        lightning_rod = [a for a in resp.abilities if a.name == "lightning-rod"][0]
        assert lightning_rod.is_hidden is True

    def test_sprites(self, service):
        resp = service.GetPokemon(pb.GetPokemonRequest(name_or_id="pikachu"))
        assert "25.png" in resp.sprites.front_default
        assert "shiny" in resp.sprites.front_shiny
        assert "back" in resp.sprites.back_default

    def test_lookup_by_id(self, service):
        resp = service.GetPokemon(pb.GetPokemonRequest(name_or_id="25"))
        assert resp.id == 25
        assert resp.name == "pikachu"


class TestGetPokemonSpecies:
    def test_basic_fields(self, service):
        resp = service.GetPokemonSpecies(pb.GetPokemonSpeciesRequest(name_or_id="pikachu"))
        assert resp.id == 25
        assert resp.name == "pikachu"
        assert resp.generation == "generation-i"
        assert resp.habitat == "forest"
        assert resp.is_legendary is False
        assert resp.is_mythical is False

    def test_flavor_text_english(self, service):
        resp = service.GetPokemonSpecies(pb.GetPokemonSpeciesRequest(name_or_id="pikachu"))
        assert "electricity" in resp.flavor_text

    def test_genus_english(self, service):
        resp = service.GetPokemonSpecies(pb.GetPokemonSpeciesRequest(name_or_id="pikachu"))
        assert resp.genus == "Mouse Pokemon"

    def test_evolution_chain_url(self, service):
        resp = service.GetPokemonSpecies(pb.GetPokemonSpeciesRequest(name_or_id="pikachu"))
        assert "evolution-chain/10" in resp.evolution_chain_url

    def test_capture_rate(self, service):
        resp = service.GetPokemonSpecies(pb.GetPokemonSpeciesRequest(name_or_id="pikachu"))
        assert resp.capture_rate == 190

    def test_color_and_shape(self, service):
        resp = service.GetPokemonSpecies(pb.GetPokemonSpeciesRequest(name_or_id="pikachu"))
        assert resp.color == "yellow"
        assert resp.shape == "quadruped"

    def test_base_happiness(self, service):
        resp = service.GetPokemonSpecies(pb.GetPokemonSpeciesRequest(name_or_id="pikachu"))
        assert resp.base_happiness == 70


class TestGetAbility:
    def test_basic_fields(self, service):
        resp = service.GetAbility(pb.GetAbilityRequest(name_or_id="static"))
        assert resp.id == 9
        assert resp.name == "static"

    def test_effect(self, service):
        resp = service.GetAbility(pb.GetAbilityRequest(name_or_id="static"))
        assert "30%" in resp.effect
        assert "paralyzing" in resp.effect

    def test_short_effect(self, service):
        resp = service.GetAbility(pb.GetAbilityRequest(name_or_id="static"))
        assert "30%" in resp.short_effect

    def test_pokemon_list(self, service):
        resp = service.GetAbility(pb.GetAbilityRequest(name_or_id="static"))
        assert len(resp.pokemon) == 3
        names = [p.name for p in resp.pokemon]
        assert "pikachu" in names
        assert "electabuzz" in names


class TestGetMove:
    def test_basic_fields(self, service):
        resp = service.GetMove(pb.GetMoveRequest(name_or_id="thunderbolt"))
        assert resp.id == 85
        assert resp.name == "thunderbolt"
        assert resp.power == 90
        assert resp.accuracy == 100
        assert resp.pp == 15

    def test_type_and_damage_class(self, service):
        resp = service.GetMove(pb.GetMoveRequest(name_or_id="thunderbolt"))
        assert resp.type == "electric"
        assert resp.damage_class == "special"

    def test_effect(self, service):
        resp = service.GetMove(pb.GetMoveRequest(name_or_id="thunderbolt"))
        assert "paralyzing" in resp.effect or "paralyze" in resp.short_effect

    def test_priority(self, service):
        resp = service.GetMove(pb.GetMoveRequest(name_or_id="thunderbolt"))
        assert resp.priority == 0


class TestGetType:
    def test_basic_fields(self, service):
        resp = service.GetType(pb.GetTypeRequest(name_or_id="electric"))
        assert resp.id == 13
        assert resp.name == "electric"

    def test_double_damage_to(self, service):
        resp = service.GetType(pb.GetTypeRequest(name_or_id="electric"))
        assert "water" in resp.damage_relations.double_damage_to
        assert "flying" in resp.damage_relations.double_damage_to

    def test_half_damage_to(self, service):
        resp = service.GetType(pb.GetTypeRequest(name_or_id="electric"))
        assert "grass" in resp.damage_relations.half_damage_to
        assert "dragon" in resp.damage_relations.half_damage_to

    def test_no_damage_to(self, service):
        resp = service.GetType(pb.GetTypeRequest(name_or_id="electric"))
        assert "ground" in resp.damage_relations.no_damage_to

    def test_double_damage_from(self, service):
        resp = service.GetType(pb.GetTypeRequest(name_or_id="electric"))
        assert "ground" in resp.damage_relations.double_damage_from

    def test_half_damage_from(self, service):
        resp = service.GetType(pb.GetTypeRequest(name_or_id="electric"))
        assert "steel" in resp.damage_relations.half_damage_from

    def test_pokemon_list(self, service):
        resp = service.GetType(pb.GetTypeRequest(name_or_id="electric"))
        assert "pikachu" in resp.pokemon
        assert "raichu" in resp.pokemon

    def test_moves_list(self, service):
        resp = service.GetType(pb.GetTypeRequest(name_or_id="electric"))
        assert "thunderbolt" in resp.moves
        assert "thunder" in resp.moves


class TestGetEvolutionChain:
    def test_chain_id(self, service):
        resp = service.GetEvolutionChain(pb.GetEvolutionChainRequest(id=10))
        assert resp.id == 10

    def test_base_species(self, service):
        resp = service.GetEvolutionChain(pb.GetEvolutionChainRequest(id=10))
        assert resp.chain.species_name == "pichu"

    def test_first_evolution(self, service):
        resp = service.GetEvolutionChain(pb.GetEvolutionChainRequest(id=10))
        assert len(resp.chain.evolves_to) == 1
        pikachu = resp.chain.evolves_to[0]
        assert pikachu.species_name == "pikachu"
        assert pikachu.trigger == "level-up"

    def test_second_evolution(self, service):
        resp = service.GetEvolutionChain(pb.GetEvolutionChainRequest(id=10))
        pikachu = resp.chain.evolves_to[0]
        assert len(pikachu.evolves_to) == 1
        raichu = pikachu.evolves_to[0]
        assert raichu.species_name == "raichu"
        assert raichu.trigger == "use-item"
        assert raichu.item == "thunder-stone"


class TestGetGeneration:
    def test_basic_fields(self, service):
        resp = service.GetGeneration(pb.GetGenerationRequest(name_or_id="generation-i"))
        assert resp.id == 1
        assert resp.name == "generation-i"
        assert resp.main_region == "kanto"

    def test_pokemon_species(self, service):
        resp = service.GetGeneration(pb.GetGenerationRequest(name_or_id="generation-i"))
        assert "bulbasaur" in resp.pokemon_species
        assert "charmander" in resp.pokemon_species
        assert "squirtle" in resp.pokemon_species

    def test_moves(self, service):
        resp = service.GetGeneration(pb.GetGenerationRequest(name_or_id="generation-i"))
        assert "pound" in resp.moves
        assert "karate-chop" in resp.moves

    def test_types(self, service):
        resp = service.GetGeneration(pb.GetGenerationRequest(name_or_id="generation-i"))
        assert "normal" in resp.types
        assert "fire" in resp.types
        assert "water" in resp.types


class TestGetItem:
    def test_basic_fields(self, service):
        resp = service.GetItem(pb.GetItemRequest(name_or_id="potion"))
        assert resp.id == 17
        assert resp.name == "potion"
        assert resp.cost == 200
        assert resp.category == "medicine"

    def test_effect(self, service):
        resp = service.GetItem(pb.GetItemRequest(name_or_id="potion"))
        assert "20" in resp.effect
        assert "HP" in resp.effect

    def test_short_effect(self, service):
        resp = service.GetItem(pb.GetItemRequest(name_or_id="potion"))
        assert "20 HP" in resp.short_effect

    def test_sprite(self, service):
        resp = service.GetItem(pb.GetItemRequest(name_or_id="potion"))
        assert "potion.png" in resp.sprite


class TestGetNature:
    def test_basic_fields(self, service):
        resp = service.GetNature(pb.GetNatureRequest(name_or_id="adamant"))
        assert resp.id == 2
        assert resp.name == "adamant"

    def test_stat_modifications(self, service):
        resp = service.GetNature(pb.GetNatureRequest(name_or_id="adamant"))
        assert resp.increased_stat == "attack"
        assert resp.decreased_stat == "special-attack"


class TestListPokemon:
    def test_returns_list(self, service):
        resp = service.ListPokemon(pb.ListPokemonRequest())
        assert resp.count == 1302
        assert len(resp.results) == 3

    def test_result_fields(self, service):
        resp = service.ListPokemon(pb.ListPokemonRequest())
        assert resp.results[0].name == "bulbasaur"
        assert "pokemon/1" in resp.results[0].url

    def test_pagination_fields(self, service):
        resp = service.ListPokemon(pb.ListPokemonRequest())
        assert "offset=20" in resp.next
        assert resp.previous == ""

    def test_default_params(self, service, mock_http):
        service.ListPokemon(pb.ListPokemonRequest())
        call_args = mock_http.get.call_args
        params = call_args[1].get("params", {})
        assert params.get("limit") == 20
        assert params.get("offset") == 0

    def test_custom_params(self, service, mock_http):
        service.ListPokemon(pb.ListPokemonRequest(limit=50, offset=100))
        call_args = mock_http.get.call_args
        params = call_args[1].get("params", {})
        assert params.get("limit") == 50
        assert params.get("offset") == 100
