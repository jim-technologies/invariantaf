"""Shared fixtures for arXiv MCP tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from arxiv_mcp.gen.arxiv.v1 import arxiv_pb2 as pb

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

# ---------------------------------------------------------------------------
# Fake API data — matches real arXiv Atom XML return shapes
# ---------------------------------------------------------------------------

FAKE_SEARCH_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/1706.03762v7</id>
    <title>Attention Is All You Need</title>
    <summary>The dominant sequence transduction models are based on complex recurrent or convolutional neural networks.</summary>
    <author><name>Ashish Vaswani</name></author>
    <author><name>Noam Shazeer</name></author>
    <author><name>Niki Parmar</name></author>
    <arxiv:primary_category term="cs.CL"/>
    <category term="cs.CL"/>
    <category term="cs.AI"/>
    <published>2017-06-12T17:57:34Z</published>
    <updated>2023-08-02T00:00:00Z</updated>
    <link title="pdf" href="http://arxiv.org/pdf/1706.03762v7" rel="related" type="application/pdf"/>
    <link href="http://arxiv.org/abs/1706.03762v7" rel="alternate" type="text/html"/>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2301.00001v1</id>
    <title>Deep Learning for Natural Language Processing</title>
    <summary>A survey of deep learning methods applied to NLP tasks.</summary>
    <author><name>Jane Smith</name></author>
    <arxiv:primary_category term="cs.CL"/>
    <category term="cs.CL"/>
    <category term="cs.LG"/>
    <published>2023-01-01T00:00:00Z</published>
    <updated>2023-01-01T00:00:00Z</updated>
    <link title="pdf" href="http://arxiv.org/pdf/2301.00001v1" rel="related" type="application/pdf"/>
    <link href="http://arxiv.org/abs/2301.00001v1" rel="alternate" type="text/html"/>
  </entry>
</feed>'''

FAKE_SINGLE_PAPER_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/1706.03762v7</id>
    <title>Attention Is All You Need</title>
    <summary>The dominant sequence transduction models are based on complex recurrent or convolutional neural networks.</summary>
    <author><name>Ashish Vaswani</name></author>
    <author><name>Noam Shazeer</name></author>
    <author><name>Niki Parmar</name></author>
    <arxiv:primary_category term="cs.CL"/>
    <category term="cs.CL"/>
    <category term="cs.AI"/>
    <published>2017-06-12T17:57:34Z</published>
    <updated>2023-08-02T00:00:00Z</updated>
    <link title="pdf" href="http://arxiv.org/pdf/1706.03762v7" rel="related" type="application/pdf"/>
    <link href="http://arxiv.org/abs/1706.03762v7" rel="alternate" type="text/html"/>
  </entry>
</feed>'''

FAKE_EMPTY_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
</feed>'''

FAKE_MULTI_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/1706.03762v7</id>
    <title>Attention Is All You Need</title>
    <summary>The dominant sequence transduction models.</summary>
    <author><name>Ashish Vaswani</name></author>
    <arxiv:primary_category term="cs.CL"/>
    <category term="cs.CL"/>
    <published>2017-06-12T17:57:34Z</published>
    <updated>2023-08-02T00:00:00Z</updated>
    <link title="pdf" href="http://arxiv.org/pdf/1706.03762v7" rel="related" type="application/pdf"/>
    <link href="http://arxiv.org/abs/1706.03762v7" rel="alternate" type="text/html"/>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2106.09685v2</id>
    <title>LoRA: Low-Rank Adaptation of Large Language Models</title>
    <summary>We propose LoRA for efficient fine-tuning.</summary>
    <author><name>Edward Hu</name></author>
    <arxiv:primary_category term="cs.CL"/>
    <category term="cs.CL"/>
    <category term="cs.AI"/>
    <category term="cs.LG"/>
    <published>2021-06-17T00:00:00Z</published>
    <updated>2021-10-16T00:00:00Z</updated>
    <link title="pdf" href="http://arxiv.org/pdf/2106.09685v2" rel="related" type="application/pdf"/>
    <link href="http://arxiv.org/abs/2106.09685v2" rel="alternate" type="text/html"/>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2005.14165v4</id>
    <title>Language Models are Few-Shot Learners</title>
    <summary>We demonstrate that scaling up language models improves task-agnostic performance.</summary>
    <author><name>Tom Brown</name></author>
    <arxiv:primary_category term="cs.CL"/>
    <category term="cs.CL"/>
    <published>2020-05-28T00:00:00Z</published>
    <updated>2020-07-22T00:00:00Z</updated>
    <link title="pdf" href="http://arxiv.org/pdf/2005.14165v4" rel="related" type="application/pdf"/>
    <link href="http://arxiv.org/abs/2005.14165v4" rel="alternate" type="text/html"/>
  </entry>
</feed>'''


def _make_mock_http(url_responses: dict | None = None):
    """Create a mock httpx.Client with configurable responses.

    The arXiv API uses a single endpoint with query params, so we match
    on the params dict to determine which fake XML to return.
    """
    http = MagicMock()

    overrides = url_responses or {}

    def mock_get(url, params=None):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()

        # Check overrides first.
        params = params or {}
        for key, xml in overrides.items():
            if key in str(params):
                resp.text = xml
                return resp

        # Default routing based on params.
        id_list = params.get("id_list", "")
        search_query = params.get("search_query", "")

        if id_list:
            # ID-based lookup.
            if "," in str(id_list):
                resp.text = FAKE_MULTI_XML
            else:
                resp.text = FAKE_SINGLE_PAPER_XML
        elif search_query:
            resp.text = FAKE_SEARCH_XML
        else:
            resp.text = FAKE_EMPTY_XML

        return resp

    http.get = MagicMock(side_effect=mock_get)
    return http


@pytest.fixture
def mock_http():
    return _make_mock_http()


@pytest.fixture
def service(mock_http):
    """ArxivService with mocked HTTP client."""
    from arxiv_mcp.service import ArxivService

    svc = ArxivService.__new__(ArxivService)
    svc._http = mock_http
    return svc


@pytest.fixture
def server(service):
    """Invariant Server with the mocked ArxivService registered."""
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-arxiv", version="0.0.1")
    srv.register(service)
    return srv
