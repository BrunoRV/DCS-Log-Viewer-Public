/**
 * highlighter_dcs.js — DCS-specific highlighting rules and instance.
 */

import { Highlighter } from './highlighter.js';

const DCS_RULES = [
  // Linkable: URLs
  {
    name: 'link',
    regex: /https?:\/\/[^\s]+/g
  },
  // Linkable: IPs (IPv4)
  {
    name: 'link',
    regex: /\b(?:\d{1,3}\.){3}\d{1,3}\b/g
  },
  // Linkable: Quoted Paths (supports spaces)
  {
    name: 'link',
    regex: /"([a-zA-Z]:[\\/][^"]+)"|'([a-zA-Z]:[\\/][^']+)'/g
  },
  // Linkable: Paths (Windows, Unix, or Relative - supports internal spaces)
  {
    name: 'link',
    regex: /\b[a-zA-Z]:[\\/](?:[^:;*?"<>|\r\n\t \[\]{}()]+|(?<=[\\/\w.-])\s+(?=[\w.-]+[\\/]))+|(?<![\w/])\/(?:[\w.-]+\/)+[\w.-]+|(?<![\w/])(?:\.\.?\/)(?:[^:;*?"<>|\r\n\t \[\]{}()]+|(?<=[\\/\w.-])\s+(?=[\w.-]+[\\/]))+/g
  },
  // Generic: Brackets [Unit]
  {
    name: 'bracket',
    regex: /\[[^\]\r\n]+\]/g
  },
  // Generic: Braces {Payload}
  {
    name: 'brace',
    regex: /\{[^\}\r\n]+\}/g
  },
  // Generic: Member access Class::Method
  {
    name: 'member',
    regex: /\b[a-zA-Z0-9_]+::[a-zA-Z0-9_]+\b/g
  },
  // Generic: Strings "..." or '...'
  {
    name: 'string',
    regex: /"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'/g
  }
];

export const dcsHighlighter = new Highlighter(DCS_RULES);
